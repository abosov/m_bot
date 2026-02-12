#!/usr/bin/env bash
set -u

SINCE="2 hours ago"
SPECIALIST_ID=""
OWNER_TG_ID=""
WITH_DB_DUMP="false"
UNITS_CSV=""
APP_DIR="/opt/zumbot/backend"

UTCSTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="/tmp/zumbot_diag_${UTCSTAMP}"
ARCHIVE_PATH="${OUT_DIR}.tar.gz"
SKIPPED_COUNT=0
FOUND_SPECIALIST_ID=""
DB_URL=""
DB_SOURCE=""

usage() {
  cat <<'USAGE'
Usage: scripts/diag_collect.sh [options]

Options:
  --since "2 hours ago"         Journal/docker lookback window (default: 2 hours ago)
  --specialist-id <id>          Specialist id for DB snapshot
  --owner-tg-id <id>            Owner Telegram id (will try to resolve specialist_id)
  --with-db-dump                Add pg_dump -Fc (if available)
  --units "u1,u2,u3"            Comma separated systemd units
  --app-dir /opt/zumbot/backend Application directory
  -h, --help                    Show this help
USAGE
}

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

resolve_specialist_id_from_owner() {
  [[ -n "$OWNER_TG_ID" ]] || return
  local psql_url
  psql_url="$(to_psql_url "$DB_URL")"
  [[ -n "$psql_url" ]] || return
  if ! command -v psql >/dev/null 2>&1; then
    log_skip "OWNER_TG_LOOKUP" "psql not available for owner_tg_id lookup"
    return
  fi

  local sql=""
  sql+="WITH candidates AS ("
  sql+=" SELECT s.id::text AS sid FROM information_schema.columns c JOIN specialist s ON true WHERE c.table_schema='public' AND c.table_name='specialist' AND c.column_name='owner_tg_id' AND s.owner_tg_id::text='${OWNER_TG_ID}'"
  sql+=") SELECT sid FROM candidates LIMIT 1;"

  local sid
  sid="$(psql "$psql_url" -At -c "$sql" 2>/dev/null | head -n1)"
  if [[ -n "$sid" ]]; then
    SPECIALIST_ID="$sid"
    FOUND_SPECIALIST_ID="$sid"
    return
  fi

  sid="$(psql "$psql_url" -At -c "SELECT specialist_id::text FROM telegram_bot WHERE owner_tg_id::text='${OWNER_TG_ID}' LIMIT 1;" 2>/dev/null | head -n1 || true)"
  if [[ -n "$sid" ]]; then
    SPECIALIST_ID="$sid"
    FOUND_SPECIALIST_ID="$sid"
  else
    log_skip "OWNER_TG_LOOKUP" "Could not resolve specialist_id from owner_tg_id=${OWNER_TG_ID}"
  fi
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

write_summary() {
  {
    echo "package_dir=${OUT_DIR}"
    echo "archive_path=${ARCHIVE_PATH}"
    echo "since=${SINCE}"
    echo "app_dir=${APP_DIR}"
    echo "units=${UNITS_CSV}"
    echo "specialist_id_input=${SPECIALIST_ID}"
    echo "owner_tg_id_input=${OWNER_TG_ID}"
    echo "resolved_specialist_id=${FOUND_SPECIALIST_ID}"
    echo "with_db_dump=${WITH_DB_DUMP}"
    echo "systemd=$([[ -f "${OUT_DIR}/SKIPPED_SYSTEMD.txt" ]] && echo skipped || echo collected)"
    echo "docker=$([[ -f "${OUT_DIR}/SKIPPED_DOCKER.txt" ]] && echo skipped || echo collected)"
    echo "nginx=$([[ -f "${OUT_DIR}/SKIPPED_NGINX.txt" ]] && echo skipped || echo collected)"
    echo "db=$([[ -f "${OUT_DIR}/SKIPPED_DB_NOT_FOUND.txt" ]] && echo skipped || echo collected)"
    echo "skipped_count=${SKIPPED_COUNT}"
  } > "${OUT_DIR}/summary.txt"
}

main() {
  parse_args "$@"
  mkdir -p "$OUT_DIR"

  collect_meta
  collect_systemd
  collect_docker
  collect_nginx
  collect_db_snapshot
  write_summary

  tar -C /tmp -czf "$ARCHIVE_PATH" "$(basename "$OUT_DIR")"

  printf '%s\n' "$ARCHIVE_PATH"
  if [[ "$SKIPPED_COUNT" -gt 0 ]]; then
    printf 'PARTIAL\n'
  else
    printf 'OK\n'
  fi
}

main "$@"
