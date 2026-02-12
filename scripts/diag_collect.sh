#!/usr/bin/env bash
set -u

SINCE="2 hours ago"
SPECIALIST_ID=""
OWNER_TG_ID=""
WITH_DB_DUMP="false"
UNITS_CSV=""
APP_DIR="/opt/zumbot/backend"
CHECK_MODE="false"
CHECK_ONLY="false"
OUTPUT_JSON="false"

UTCSTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="/tmp/zumbot_diag_${UTCSTAMP}"
ARCHIVE_PATH="${OUT_DIR}.tar.gz"
SKIPPED_COUNT=0
INPUT_SPECIALIST_ID=""
RESOLVED_SPECIALIST_ID=""
DB_URL=""
DB_SOURCE=""

CHECK_STARTED_AT=""
CHECK_FINISHED_AT=""
CHECK_OVERALL="PASS"
CHECK_FAILURES=()
CHECK_WARNINGS=()
CHECK_PASSES=()
CHECK_FAILURE_DETAILS=()

usage() {
  cat <<'USAGE'
Usage: scripts/diag_collect.sh [options]

Options:
  --since "2 hours ago"         Journal/docker lookback window (default: 2 hours ago)
  --specialist-id <id>          Specialist id for DB snapshot/check
  --owner-tg-id <id>            Owner Telegram id (will try to resolve specialist_id)
  --with-db-dump                Add pg_dump -Fc (if available)
  --units "u1,u2,u3"            Comma separated systemd units
  --app-dir /opt/zumbot/backend Application directory
  --check                       Run DB checks and compute PASS/WARN/FAIL
  --check-only                  Run only checks (no logs and no archive)
  --json                        Write verdict to summary.json
  -h, --help                    Show this help
USAGE
}

json_escape() {
  python3 - "$1" <<'PY'
import json
import sys
print(json.dumps(sys.argv[1]))
PY
}

push_pass() { CHECK_PASSES+=("$1"); }
push_warn() { CHECK_WARNINGS+=("$1"); [[ "$CHECK_OVERALL" == "PASS" ]] && CHECK_OVERALL="WARN"; }
push_fail() { CHECK_FAILURES+=("$1"); CHECK_OVERALL="FAIL"; }

log_skip() {
  local name="$1"
  local message="$2"
  SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
  printf '%s\n' "$message" > "${OUT_DIR}/SKIPPED_${name}.txt"
}

mask_db_url() {
  local url="$1"
  python3 - "$url" <<'PY'
import sys
from urllib.parse import urlsplit, urlunsplit
url = sys.argv[1]
if not url:
    print("")
    raise SystemExit(0)
parts = urlsplit(url)
username = parts.username or ""
password = parts.password
host = parts.hostname or ""
port = f":{parts.port}" if parts.port else ""
userinfo = ""
if username:
    userinfo = username
    if password is not None:
        userinfo += ":***"
    userinfo += "@"
netloc = f"{userinfo}{host}{port}"
print(urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment)))
PY
}

to_psql_url() {
  local url="$1"
  url="${url/postgresql+asyncpg:/postgresql:}"
  url="${url/postgres+asyncpg:/postgres:}"
  if [[ "$url" == postgres://* ]]; then
    url="postgresql://${url#postgres://}"
  fi
  printf '%s' "$url"
}

sql_escape_literal() {
  printf "%s" "$1" | sed "s/'/''/g"
}

is_active_status() {
  local status
  status="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  [[ "$status" == "active" || "$status" == "enabled" || "$status" == "connected" ]]
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --since)
        SINCE="${2:-}"
        shift 2
        ;;
      --specialist-id)
        SPECIALIST_ID="${2:-}"
        shift 2
        ;;
      --owner-tg-id)
        OWNER_TG_ID="${2:-}"
        shift 2
        ;;
      --with-db-dump)
        WITH_DB_DUMP="true"
        shift
        ;;
      --units)
        UNITS_CSV="${2:-}"
        shift 2
        ;;
      --app-dir)
        APP_DIR="${2:-}"
        shift 2
        ;;
      --check)
        CHECK_MODE="true"
        shift
        ;;
      --check-only)
        CHECK_MODE="true"
        CHECK_ONLY="true"
        shift
        ;;
      --json)
        OUTPUT_JSON="true"
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        echo "Unknown argument: $1" >&2
        usage >&2
        exit 1
        ;;
    esac
  done
  INPUT_SPECIALIST_ID="$SPECIALIST_ID"
}

collect_meta() {
  {
    echo "timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "hostname=$(hostname 2>/dev/null || true)"
    echo "uname=$(uname -a 2>/dev/null || true)"
    echo "uptime=$(uptime 2>/dev/null || true)"
  } > "${OUT_DIR}/meta.txt"

  if [[ -d "${APP_DIR}/.git" ]] && command -v git >/dev/null 2>&1; then
    (cd "$APP_DIR" && git rev-parse HEAD) > "${OUT_DIR}/git_head.txt" 2>/dev/null || log_skip "GIT" "git rev-parse failed for ${APP_DIR}"
  else
    log_skip "GIT" "No git metadata at ${APP_DIR}"
  fi

  if command -v python3 >/dev/null 2>&1; then
    python3 --version > "${OUT_DIR}/python_version.txt" 2>&1 || log_skip "PYTHON_VERSION" "python3 --version failed"
    if command -v pip >/dev/null 2>&1; then
      pip freeze > "${OUT_DIR}/pip_freeze.txt" 2>&1 || log_skip "PIP_FREEZE" "pip freeze failed"
    elif command -v pip3 >/dev/null 2>&1; then
      pip3 freeze > "${OUT_DIR}/pip_freeze.txt" 2>&1 || log_skip "PIP_FREEZE" "pip3 freeze failed"
    else
      log_skip "PIP_FREEZE" "pip/pip3 not found"
    fi
  else
    log_skip "PYTHON" "python3 not found"
  fi
}

detect_units() {
  if [[ -n "$UNITS_CSV" ]]; then
    return
  fi
  if ! command -v systemctl >/dev/null 2>&1; then
    return
  fi
  UNITS_CSV="$(systemctl list-units --type=service --all --no-legend 2>/dev/null | awk '{print $1}' | rg -i '(zumbot|calendar|backend|master|personal)' | paste -sd ',' -)"
}

collect_systemd() {
  if ! command -v systemctl >/dev/null 2>&1; then
    log_skip "SYSTEMD" "systemctl not available"
    return
  fi

  detect_units
  if [[ -z "$UNITS_CSV" ]]; then
    log_skip "SYSTEMD" "No units detected"
    return
  fi

  IFS=',' read -r -a units <<< "$UNITS_CSV"
  local any="false"
  for unit in "${units[@]}"; do
    [[ -z "$unit" ]] && continue
    any="true"
    systemctl status "$unit" --no-pager > "${OUT_DIR}/systemctl_status_${unit}.txt" 2>&1 || true
    journalctl -u "$unit" --since "$SINCE" --no-pager > "${OUT_DIR}/journal_${unit}.log" 2>&1 || true
  done
  if [[ "$any" != "true" ]]; then
    log_skip "SYSTEMD" "Unit list resolved empty"
  fi
}

collect_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    log_skip "DOCKER" "docker not installed"
    return
  fi

  docker ps > "${OUT_DIR}/docker_ps.txt" 2>&1 || {
    log_skip "DOCKER" "docker ps failed"
    return
  }

  local ids
  ids="$(docker ps --format '{{.ID}} {{.Names}}' | rg -i '(zumbot|master|personal|backend)' | awk '{print $1}')"
  if [[ -z "$ids" ]]; then
    log_skip "DOCKER_CONTAINERS" "No matching containers for zumbot/master/personal/backend"
    return
  fi

  local cid
  while IFS= read -r cid; do
    [[ -z "$cid" ]] && continue
    docker logs --since "$SINCE" "$cid" > "${OUT_DIR}/docker_logs_${cid}.log" 2>&1 || true
  done <<< "$ids"
}

collect_nginx() {
  if ! command -v nginx >/dev/null 2>&1; then
    log_skip "NGINX" "nginx command not found"
    return
  fi

  nginx -t > "${OUT_DIR}/nginx_test.txt" 2>&1 || true

  local found="false"
  for path in \
    /var/log/nginx/access.log \
    /var/log/nginx/error.log \
    /usr/local/var/log/nginx/access.log \
    /usr/local/var/log/nginx/error.log; do
    if [[ -f "$path" ]]; then
      found="true"
      tail -n 200 "$path" > "${OUT_DIR}/nginx_$(basename "$path")" 2>&1 || true
    fi
  done

  if [[ "$found" != "true" ]]; then
    log_skip "NGINX" "Nginx log files not found"
  fi
}

extract_db_url_from_env_file() {
  local env_file="$1"
  [[ -f "$env_file" ]] || return 1
  local raw
  raw="$(awk -F= '/^(DB_URL|DATABASE_URL)=/ {sub(/^[^=]+= */, "", $0); print; exit}' "$env_file")"
  raw="${raw%\"}"
  raw="${raw#\"}"
  raw="${raw%\'}"
  raw="${raw#\'}"
  if [[ -n "$raw" ]]; then
    DB_URL="$raw"
    DB_SOURCE="${env_file}"
    return 0
  fi
  return 1
}

extract_db_url_from_systemd() {
  [[ -n "$UNITS_CSV" ]] || return 1
  IFS=',' read -r -a units <<< "$UNITS_CSV"
  local unit
  for unit in "${units[@]}"; do
    [[ -z "$unit" ]] && continue
    local raw
    raw="$(systemctl cat "$unit" 2>/dev/null | awk -F= '/(DB_URL|DATABASE_URL)=/ {sub(/.*(DB_URL|DATABASE_URL)=/, "", $0); print; exit}')"
    if [[ -n "$raw" ]]; then
      raw="${raw%\"}"; raw="${raw#\"}"; raw="${raw%\'}"; raw="${raw#\'}"
      DB_URL="$raw"
      DB_SOURCE="systemd:${unit}"
      return 0
    fi
  done
  return 1
}

find_db_url() {
  extract_db_url_from_env_file "${APP_DIR}/.env" && return
  extract_db_url_from_env_file "${APP_DIR}/../.env" && return
  extract_db_url_from_systemd && return
  if [[ -n "${DB_URL:-}" ]]; then
    DB_SOURCE="env:DB_URL"
    return
  fi
  if [[ -n "${DATABASE_URL:-}" ]]; then
    DB_URL="$DATABASE_URL"
    DB_SOURCE="env:DATABASE_URL"
    return
  fi
}

write_env_hints() {
  {
    echo "app_dir=${APP_DIR}"
    echo "since=${SINCE}"
    echo "units=${UNITS_CSV}"
    if [[ -n "$DB_URL" ]]; then
      echo "db_url_masked=$(mask_db_url "$DB_URL")"
      echo "db_source=${DB_SOURCE}"
    else
      echo "db_url_masked="
      echo "db_source=not_found"
    fi
  } > "${OUT_DIR}/env_hints.txt"
}

run_db_health() {
  local psql_url
  psql_url="$(to_psql_url "$DB_URL")"
  if command -v psql >/dev/null 2>&1; then
    PGPASSWORD="" psql "$psql_url" -v ON_ERROR_STOP=1 -c 'select now();' > "${OUT_DIR}/db_healthcheck.txt" 2>&1 || log_skip "DB_HEALTHCHECK" "psql select now() failed"
    return
  fi

  if command -v python3 >/dev/null 2>&1; then
    python3 - "$DB_URL" > "${OUT_DIR}/db_healthcheck.txt" 2>&1 <<'PY' || log_skip "DB_HEALTHCHECK" "python asyncpg health-check failed"
import asyncio
import sys
url = sys.argv[1]
async def main():
    import asyncpg  # type: ignore
    conn = await asyncpg.connect(url)
    val = await conn.fetchval('select now()')
    await conn.close()
    print(f"now={val}")
asyncio.run(main())
PY
  else
    log_skip "DB_HEALTHCHECK" "Neither psql nor python3 available"
  fi
}

resolve_specialist_id_from_owner_psql() {
  local psql_url owner_escaped sid
  psql_url="$(to_psql_url "$DB_URL")"
  owner_escaped="$(sql_escape_literal "$OWNER_TG_ID")"
  sid="$(psql "$psql_url" -At -F '|' -v ON_ERROR_STOP=1 -c "SELECT s.id::text FROM specialist s WHERE s.owner_tg_id::text='${owner_escaped}' LIMIT 1;" 2>/dev/null | head -n1 || true)"
  if [[ -z "$sid" ]]; then
    sid="$(psql "$psql_url" -At -F '|' -v ON_ERROR_STOP=1 -c "SELECT tb.specialist_id::text FROM telegram_bot tb WHERE tb.owner_tg_id::text='${owner_escaped}' LIMIT 1;" 2>/dev/null | head -n1 || true)"
  fi
  [[ -n "$sid" ]] && { SPECIALIST_ID="$sid"; RESOLVED_SPECIALIST_ID="$sid"; return 0; }
  return 1
}

resolve_specialist_id_from_owner_python() {
  python3 - "$DB_URL" "$OWNER_TG_ID" <<'PY'
import asyncio
import sys

async def main(db_url: str, owner_tg_id: str) -> None:
    import asyncpg  # type: ignore

    conn = await asyncpg.connect(db_url)
    sid = await conn.fetchval("SELECT s.id::text FROM specialist s WHERE s.owner_tg_id::text=$1 LIMIT 1", owner_tg_id)
    if not sid:
      sid = await conn.fetchval("SELECT tb.specialist_id::text FROM telegram_bot tb WHERE tb.owner_tg_id::text=$1 LIMIT 1", owner_tg_id)
    await conn.close()
    if sid:
      print(sid)

asyncio.run(main(sys.argv[1], sys.argv[2]))
PY
}

resolve_specialist_id_from_owner() {
  [[ -n "$OWNER_TG_ID" ]] || return
  [[ -n "$DB_URL" ]] || return

  if command -v psql >/dev/null 2>&1; then
    resolve_specialist_id_from_owner_psql && return
  fi

  if command -v python3 >/dev/null 2>&1; then
    local sid
    sid="$(resolve_specialist_id_from_owner_python 2>/dev/null | head -n1 || true)"
    if [[ -n "$sid" ]]; then
      SPECIALIST_ID="$sid"
      RESOLVED_SPECIALIST_ID="$sid"
      return
    fi
  fi
  log_skip "OWNER_TG_LOOKUP" "Could not resolve specialist_id from owner_tg_id=${OWNER_TG_ID}"
}

collect_db_snapshot() {
  find_db_url
  write_env_hints

  if [[ -z "$DB_URL" ]]; then
    log_skip "DB_NOT_FOUND" "DB_URL not found in ${APP_DIR}/.env, systemd units, or environment"
    return
  fi

  run_db_health
  resolve_specialist_id_from_owner

  if [[ -n "$SPECIALIST_ID" ]] && command -v psql >/dev/null 2>&1; then
    local psql_url
    psql_url="$(to_psql_url "$DB_URL")"
    psql "$psql_url" -v ON_ERROR_STOP=0 -v specialist_id="$SPECIALIST_ID" -f "${APP_DIR}/scripts/diag_db_snapshot.sql" > "${OUT_DIR}/db_snapshot_${SPECIALIST_ID}.txt" 2>&1 || true
  elif [[ -n "$SPECIALIST_ID" ]]; then
    log_skip "DB_SNAPSHOT" "psql not available for SQL snapshot"
  else
    log_skip "DB_SNAPSHOT" "specialist_id not provided/resolved"
  fi

  if [[ "$WITH_DB_DUMP" == "true" ]]; then
    local psql_url
    psql_url="$(to_psql_url "$DB_URL")"
    if command -v pg_dump >/dev/null 2>&1; then
      pg_dump -Fc "$psql_url" -f "${OUT_DIR}/db.dump" > "${OUT_DIR}/db_dump.log" 2>&1 || log_skip "DB_DUMP" "pg_dump failed"
    else
      log_skip "DB_DUMP" "pg_dump not found"
    fi
  fi
}

run_db_check_psql() {
  local psql_url
  psql_url="$(to_psql_url "$DB_URL")"
  psql "$psql_url" -At -F '|' -v ON_ERROR_STOP=1 -v specialist_id="$SPECIALIST_ID" -f "${APP_DIR}/scripts/diag_db_check.sql"
}

run_db_check_python() {
  python3 - "$DB_URL" "$SPECIALIST_ID" <<'PY'
import asyncio
import sys

async def main(db_url: str, specialist_id: str) -> None:
    import asyncpg  # type: ignore

    conn = await asyncpg.connect(db_url)
    specialist = await conn.fetchrow("SELECT id::text AS specialist_id, status::text AS specialist_status FROM specialist WHERE id::text=$1", specialist_id)
    profile = await conn.fetchrow(
        """
        SELECT specialist_id::text, specialist_timezone::text, session_duration_min, session_buffer_min,
               slot_step_min, max_sessions_per_day, cancel_window_hours
        FROM specialist_profile
        WHERE specialist_id::text=$1
        """,
        specialist_id,
    )
    calendar = await conn.fetchrow(
        "SELECT specialist_id::text, calendar_id::text, calendar_time_zone::text FROM specialist_calendar_settings WHERE specialist_id::text=$1",
        specialist_id,
    )
    bot = await conn.fetchrow("SELECT specialist_id::text, status::text AS bot_status FROM telegram_bot WHERE specialist_id::text=$1 LIMIT 1", specialist_id)
    weekly = await conn.fetch(
        """
        SELECT weekday, interval_1_start_local, interval_1_end_local,
               interval_2_start_local, interval_2_end_local,
               interval_3_start_local, interval_3_end_local
        FROM weekly_availability
        WHERE specialist_id::text=$1
        ORDER BY weekday
        """,
        specialist_id,
    )
    policy_persisted = await conn.fetchval(
        """
        SELECT CASE
          WHEN to_regclass('public.booking_policy') IS NOT NULL THEN 'true'
          WHEN EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema='public'
              AND table_name='specialist_profile'
              AND column_name IN ('next_day_cutoff_hour', 'next_day_cutoff_time', 'booking_cutoff_hour')
          ) THEN 'true'
          ELSE 'false'
        END
        """
    )
    await conn.close()

    invalid = []
    for r in weekly:
        vals = [
            (r['interval_1_start_local'], r['interval_1_end_local']),
            (r['interval_2_start_local'], r['interval_2_end_local']),
            (r['interval_3_start_local'], r['interval_3_end_local']),
        ]
        if any((a is None) != (b is None) for a, b in vals):
            invalid.append(
                f"weekday={r['weekday']} i1={r['interval_1_start_local'] or 'NULL'}/{r['interval_1_end_local'] or 'NULL'} "
                f"i2={r['interval_2_start_local'] or 'NULL'}/{r['interval_2_end_local'] or 'NULL'} "
                f"i3={r['interval_3_start_local'] or 'NULL'}/{r['interval_3_end_local'] or 'NULL'}"
            )

    rows = {
        'specialist_exists': 'true' if specialist else 'false',
        'specialist_status': specialist['specialist_status'] if specialist else '',
        'bot_exists': 'true' if bot else 'false',
        'bot_status': bot['bot_status'] if bot else '',
        'calendar_exists': 'true' if calendar else 'false',
        'calendar_id': calendar['calendar_id'] if calendar and calendar['calendar_id'] else '',
        'calendar_time_zone': calendar['calendar_time_zone'] if calendar and calendar['calendar_time_zone'] else '',
        'profile_exists': 'true' if profile else 'false',
        'profile_timezone': profile['specialist_timezone'] if profile and profile['specialist_timezone'] else '',
        'session_duration_min': str(profile['session_duration_min']) if profile and profile['session_duration_min'] is not None else '',
        'session_buffer_min': str(profile['session_buffer_min']) if profile and profile['session_buffer_min'] is not None else '',
        'slot_step_min': str(profile['slot_step_min']) if profile and profile['slot_step_min'] is not None else '',
        'max_sessions_per_day': str(profile['max_sessions_per_day']) if profile and profile['max_sessions_per_day'] is not None else '',
        'cancel_window_hours': str(profile['cancel_window_hours']) if profile and profile['cancel_window_hours'] is not None else '',
        'weekly_count': str(len(weekly)),
        'weekly_invalid_xor_count': str(len(invalid)),
        'weekly_invalid_rows': '; '.join(invalid),
        'policy_persisted': policy_persisted or 'false',
    }
    for k, v in rows.items():
        print(f"{k}|{v}")

asyncio.run(main(sys.argv[1], sys.argv[2]))
PY
}

run_db_check() {
  local result_path="${OUT_DIR}/db_check_raw.txt"
  if command -v psql >/dev/null 2>&1; then
    run_db_check_psql > "$result_path" 2>"${OUT_DIR}/db_check_error.log" && return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    run_db_check_python > "$result_path" 2>"${OUT_DIR}/db_check_error.log" && return 0
  fi
  return 1
}

check_numeric_gt_zero() {
  local value="$1"
  [[ "$value" =~ ^[0-9]+$ ]] && (( value > 0 ))
}

check_numeric_ge_zero() {
  local value="$1"
  [[ "$value" =~ ^[0-9]+$ ]] && (( value >= 0 ))
}

append_check_results() {
  local summary_path="${OUT_DIR}/summary.txt"
  {
    echo ""
    echo "CHECK RESULTS:"
    echo "  OVERALL: ${CHECK_OVERALL}"
    echo "  specialist_id: ${SPECIALIST_ID:-}"
    echo "  owner_tg_id: ${OWNER_TG_ID:-}"
    echo "  checks:"
    local item
    for item in "${CHECK_PASSES[@]}"; do
      echo "    - [PASS] ${item}"
    done
    for item in "${CHECK_WARNINGS[@]}"; do
      echo "    - [WARN] ${item}"
    done
    for item in "${CHECK_FAILURES[@]}"; do
      echo "    - [FAIL] ${item}"
    done
  } >> "$summary_path"
}

write_summary_json() {
  local path="${OUT_DIR}/summary.json"
  {
    echo "{"
    echo "  \"overall\": \"${CHECK_OVERALL}\"," 
    echo "  \"specialist_id\": $(json_escape "${SPECIALIST_ID:-}"),"
    echo "  \"owner_tg_id\": $(json_escape "${OWNER_TG_ID:-}"),"
    echo "  \"started_at\": $(json_escape "${CHECK_STARTED_AT:-}"),"
    echo "  \"finished_at\": $(json_escape "${CHECK_FINISHED_AT:-}"),"

    echo "  \"failures\": ["
    local i
    for i in "${!CHECK_FAILURES[@]}"; do
      printf '    %s' "$(json_escape "${CHECK_FAILURES[$i]}")"
      [[ "$i" -lt $((${#CHECK_FAILURES[@]} - 1)) ]] && printf ','
      echo
    done
    echo "  ],"

    echo "  \"warnings\": ["
    for i in "${!CHECK_WARNINGS[@]}"; do
      printf '    %s' "$(json_escape "${CHECK_WARNINGS[$i]}")"
      [[ "$i" -lt $((${#CHECK_WARNINGS[@]} - 1)) ]] && printf ','
      echo
    done
    echo "  ],"

    echo "  \"passes\": ["
    for i in "${!CHECK_PASSES[@]}"; do
      printf '    %s' "$(json_escape "${CHECK_PASSES[$i]}")"
      [[ "$i" -lt $((${#CHECK_PASSES[@]} - 1)) ]] && printf ','
      echo
    done
    echo "  ]"
    echo "}"
  } > "$path"
}

perform_checks() {
  CHECK_STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

  find_db_url
  write_env_hints
  if [[ -z "$DB_URL" ]]; then
    push_fail "DB_URL not found"
    CHECK_FINISHED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    return
  fi

  if [[ -z "$SPECIALIST_ID" && -n "$OWNER_TG_ID" ]]; then
    resolve_specialist_id_from_owner
  fi
  if [[ -z "$SPECIALIST_ID" ]]; then
    push_fail "specialist_id is required (pass --specialist-id or resolvable --owner-tg-id)"
    CHECK_FINISHED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    return
  fi

  if ! run_db_check; then
    push_fail "DB check query failed (psql/python unavailable or query error)"
    CHECK_FINISHED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    return
  fi

  declare -A KV=()
  while IFS='|' read -r k v; do
    [[ -z "$k" ]] && continue
    KV["$k"]="$v"
  done < "${OUT_DIR}/db_check_raw.txt"

  if [[ "${KV[specialist_exists]:-false}" == "true" ]]; then
    push_pass "specialist exists"
  else
    push_fail "specialist not found"
  fi

  if is_active_status "${KV[specialist_status]:-}"; then
    push_pass "specialist status active"
  else
    push_fail "specialist status is not active (${KV[specialist_status]:-empty})"
  fi

  if [[ "${KV[bot_exists]:-false}" == "true" ]]; then
    push_pass "personal bot exists"
  else
    push_fail "personal bot missing"
  fi

  if is_active_status "${KV[bot_status]:-}"; then
    push_pass "personal bot active"
  else
    push_fail "personal bot status is not active (${KV[bot_status]:-empty})"
  fi

  if [[ "${KV[calendar_exists]:-false}" == "true" ]]; then
    push_pass "calendar settings exist"
  else
    push_fail "calendar settings missing"
  fi

  if [[ -n "${KV[calendar_id]:-}" ]]; then
    push_pass "calendar_id is set"
  else
    push_fail "calendar_id is empty"
  fi

  if [[ -n "${KV[calendar_time_zone]:-}" ]]; then
    push_pass "calendar_time_zone is set"
  elif [[ -n "${KV[profile_timezone]:-}" || "${KV[profile_timezone]:-}" == "UTC" ]]; then
    push_warn "calendar_time_zone missing, profile timezone fallback used"
  else
    push_fail "calendar_time_zone missing and profile timezone missing"
  fi

  if [[ "${KV[profile_exists]:-false}" != "true" ]]; then
    push_fail "specialist_profile missing"
  else
    push_pass "specialist_profile exists"
  fi

  if [[ -n "${KV[profile_timezone]:-}" ]]; then
    push_pass "specialist_timezone is set"
  else
    push_fail "specialist_timezone is empty"
  fi

  check_numeric_gt_zero "${KV[session_duration_min]:-}" && push_pass "session_duration_min > 0" || push_fail "session_duration_min invalid"
  check_numeric_ge_zero "${KV[session_buffer_min]:-}" && push_pass "session_buffer_min >= 0" || push_fail "session_buffer_min invalid"
  if [[ "${KV[slot_step_min]:-}" =~ ^(60|30|15|10)$ ]]; then
    push_pass "slot_step_min is allowed"
  else
    push_fail "slot_step_min invalid (${KV[slot_step_min]:-empty})"
  fi
  check_numeric_gt_zero "${KV[max_sessions_per_day]:-}" && push_pass "max_sessions_per_day > 0" || push_fail "max_sessions_per_day invalid"
  check_numeric_gt_zero "${KV[cancel_window_hours]:-}" && push_pass "cancel_window_hours > 0" || push_fail "cancel_window_hours invalid"

  if [[ "${KV[weekly_count]:-0}" == "7" ]]; then
    push_pass "weekly availability has 7 rows"
  else
    push_fail "weekly availability rows count is ${KV[weekly_count]:-0}, expected 7"
  fi

  if [[ "${KV[weekly_invalid_xor_count]:-0}" == "0" ]]; then
    push_pass "weekly availability intervals are NULL/NULL consistent"
  else
    push_fail "weekly availability has XOR-NULL interval rows: ${KV[weekly_invalid_rows]:-details missing}"
  fi

  if [[ "${KV[policy_persisted]:-false}" == "true" ]]; then
    push_pass "booking cutoff policy is persisted in DB"
  else
    push_warn "policy not persisted"
  fi

  CHECK_FINISHED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}

write_summary() {
  {
    echo "package_dir=${OUT_DIR}"
    echo "archive_path=${ARCHIVE_PATH}"
    echo "since=${SINCE}"
    echo "app_dir=${APP_DIR}"
    echo "units=${UNITS_CSV}"
    echo "specialist_id_input=${INPUT_SPECIALIST_ID}"
    echo "specialist_id_effective=${SPECIALIST_ID}"
    echo "owner_tg_id_input=${OWNER_TG_ID}"
    echo "resolved_specialist_id=${RESOLVED_SPECIALIST_ID}"
    echo "with_db_dump=${WITH_DB_DUMP}"
    echo "check_mode=${CHECK_MODE}"
    echo "check_only=${CHECK_ONLY}"
    echo "json_enabled=${OUTPUT_JSON}"
    echo "systemd=$([[ -f "${OUT_DIR}/SKIPPED_SYSTEMD.txt" ]] && echo skipped || echo collected)"
    echo "docker=$([[ -f "${OUT_DIR}/SKIPPED_DOCKER.txt" ]] && echo skipped || echo collected)"
    echo "nginx=$([[ -f "${OUT_DIR}/SKIPPED_NGINX.txt" ]] && echo skipped || echo collected)"
    echo "db=$([[ -f "${OUT_DIR}/SKIPPED_DB_NOT_FOUND.txt" ]] && echo skipped || echo collected)"
    echo "skipped_count=${SKIPPED_COUNT}"
  } > "${OUT_DIR}/summary.txt"

  if [[ "$CHECK_MODE" == "true" ]]; then
    append_check_results
  fi
}

exit_code_for_check() {
  case "$CHECK_OVERALL" in
    PASS) return 0 ;;
    WARN) return 10 ;;
    FAIL) return 20 ;;
    *) return 20 ;;
  esac
}

main() {
  parse_args "$@"
  mkdir -p "$OUT_DIR"

  if [[ "$CHECK_ONLY" != "true" ]]; then
    collect_meta
    collect_systemd
    collect_docker
    collect_nginx
    collect_db_snapshot
  else
    find_db_url
    write_env_hints
    if [[ -n "$DB_URL" ]]; then
      run_db_health
      resolve_specialist_id_from_owner
    fi
  fi

  if [[ "$CHECK_MODE" == "true" ]]; then
    perform_checks
  fi

  write_summary
  if [[ "$OUTPUT_JSON" == "true" && "$CHECK_MODE" == "true" ]]; then
    write_summary_json
  fi

  if [[ "$CHECK_ONLY" != "true" ]]; then
    tar -C /tmp -czf "$ARCHIVE_PATH" "$(basename "$OUT_DIR")"
  fi

  if [[ "$CHECK_MODE" == "true" ]]; then
    if [[ "$CHECK_ONLY" != "true" ]]; then
      printf '%s\n' "$ARCHIVE_PATH"
    fi
    printf 'OVERALL: %s\n' "$CHECK_OVERALL"
    if [[ "$CHECK_OVERALL" == "FAIL" ]]; then
      printf 'See summary.txt in archive\n'
    fi
    exit_code_for_check
    exit $?
  fi

  printf '%s\n' "$ARCHIVE_PATH"
  if [[ "$SKIPPED_COUNT" -gt 0 ]]; then
    printf 'PARTIAL\n'
  else
    printf 'OK\n'
  fi
}

main "$@"
