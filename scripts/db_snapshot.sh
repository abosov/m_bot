#!/usr/bin/env bash
set -euo pipefail

DB_URL="${DB_URL:-}"
OUT_PATH=""
DAYS=""
ENV_FILE="/etc/zumbot/backend.env"
DB_URL_OVERRIDE=""
RAW_DUMP="false"

usage() {
  cat <<'USAGE'
Usage: scripts/db_snapshot.sh [--env-file PATH] [--db-url URL] [--out PATH] [--days N] [--raw]

Options:
  --env-file PATH   Source env file before DB_URL validation (default: /etc/zumbot/backend.env)
  --db-url URL      Override DB_URL from env/env-file
  --out PATH        Output file path
  --days N          PostgreSQL only: dump only recent records
  --raw             Keep pg_dump output as-is (including \restrict/\unrestrict)
  -h, --help        Show this help

SQLite:
  Creates /tmp/zumbot_snapshot.db using sqlite3 .backup.

PostgreSQL:
  Creates /tmp/zumbot_logs_dump.sql using pg_dump (data-only for log tables).
  Use --days to dump only recent records.

Default PostgreSQL mode removes pg_dump session lines '\restrict'/'\unrestrict'.
Use --raw to preserve original output.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file)
      ENV_FILE="$2"
      shift 2
      ;;
    --db-url)
      DB_URL_OVERRIDE="$2"
      shift 2
      ;;
    --out)
      OUT_PATH="$2"
      shift 2
      ;;
    --days)
      DAYS="$2"
      shift 2
      ;;
    --raw)
      RAW_DUMP="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "${DB_URL}" && -z "${DB_URL_OVERRIDE}" && -n "${ENV_FILE}" ]]; then
  if [[ ! -f "${ENV_FILE}" ]]; then
    echo "Env file does not exist: ${ENV_FILE}" >&2
    echo "DB_URL is not set. Use --db-url <URL> or provide an existing --env-file <PATH>." >&2
    exit 1
  fi
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
  DB_URL="${DB_URL:-}"
fi

if [[ -n "${DB_URL_OVERRIDE}" ]]; then
  DB_URL="${DB_URL_OVERRIDE}"
fi

if [[ -z "${DB_URL}" ]]; then
  echo "DB_URL is not set. Use --env-file /etc/zumbot/backend.env or --db-url <URL>." >&2
  exit 1
fi

if [[ "${DB_URL}" == sqlite* ]]; then
  OUT_PATH="${OUT_PATH:-/tmp/zumbot_snapshot.db}"
  DB_PATH="${DB_URL#sqlite+aiosqlite:///}"
  DB_PATH="${DB_PATH#sqlite:///}"
  if [[ -z "${DB_PATH}" ]]; then
    echo "Unable to parse sqlite path from DB_URL." >&2
    exit 1
  fi
  if ! command -v sqlite3 >/dev/null 2>&1; then
    echo "sqlite3 is required for sqlite snapshots." >&2
    exit 1
  fi

  sqlite3 "${DB_PATH}" ".backup '${OUT_PATH}'"

  size_bytes="$(wc -c < "${OUT_PATH}" | tr -d ' ')"
  echo "SQLite snapshot: ${OUT_PATH}"
  echo "Size: ${size_bytes} bytes"
  exit 0
fi

if [[ "${DB_URL}" == postgres* ]]; then
  OUT_PATH="${OUT_PATH:-/tmp/zumbot_logs_dump.sql}"
  if ! command -v pg_dump >/dev/null 2>&1; then
    echo "pg_dump is required for postgres snapshots." >&2
    exit 1
  fi

  PG_DUMP_URL="${DB_URL/postgresql+asyncpg:/postgresql:}"
  PG_DUMP_URL="${PG_DUMP_URL/postgres+asyncpg:/postgres:}"
  if [[ "${PG_DUMP_URL}" == postgres://* ]]; then
    PG_DUMP_URL="postgresql://${PG_DUMP_URL#postgres://}"
  fi
  TMP_DUMP_PATH="$(mktemp)"
  trap 'rm -f "${TMP_DUMP_PATH}"' EXIT

  : > "${TMP_DUMP_PATH}"
  echo "-- Zumbot logs snapshot" >> "${TMP_DUMP_PATH}"
  echo "-- Generated at $(date -u +"%Y-%m-%dT%H:%M:%SZ")" >> "${TMP_DUMP_PATH}"
  echo "-- Tables: message_logs(created_at), service_heartbeats(ts), bot_health_checks(checked_at)" >> "${TMP_DUMP_PATH}"
  if [[ -n "${DAYS}" ]]; then
    echo "-- Range: last ${DAYS} days" >> "${TMP_DUMP_PATH}"
  else
    echo "-- Range: all available records" >> "${TMP_DUMP_PATH}"
  fi

  dump_table() {
    local table_name="$1"
    local ts_column="$2"
    local where_clause=""
    if [[ -n "${DAYS}" ]]; then
      where_clause="${ts_column} >= (now() - interval '${DAYS} days')"
    fi

    local dump_opts=(
      --dbname="${PG_DUMP_URL}"
      --data-only
      --no-owner
      --no-privileges
      --column-inserts
      --quote-all-identifiers
      --table="${table_name}"
    )

    if [[ -n "${where_clause}" ]]; then
      dump_opts+=(--where="${where_clause}")
    fi

    pg_dump "${dump_opts[@]}" >> "${TMP_DUMP_PATH}"
  }

  dump_table "message_logs" "created_at"
  dump_table "service_heartbeats" "ts"
  dump_table "bot_health_checks" "checked_at"

  umask 077
  if [[ "${RAW_DUMP}" == "true" ]]; then
    cp "${TMP_DUMP_PATH}" "${OUT_PATH}"
  else
    sed -E '/^(\\restrict|\\unrestrict)\b/d' "${TMP_DUMP_PATH}" > "${OUT_PATH}"
  fi
  chmod 600 "${OUT_PATH}"

  size_bytes="$(wc -c < "${OUT_PATH}" | tr -d ' ')"
  message_logs_inserts="$(grep -c '^INSERT INTO "message_logs"' "${OUT_PATH}" || true)"
  service_heartbeats_inserts="$(grep -c '^INSERT INTO "service_heartbeats"' "${OUT_PATH}" || true)"
  bot_health_checks_inserts="$(grep -c '^INSERT INTO "bot_health_checks"' "${OUT_PATH}" || true)"

  echo "PostgreSQL logs dump: ${OUT_PATH}"
  echo "Mode: $([[ "${RAW_DUMP}" == "true" ]] && echo raw || echo clean)"
  echo "Size: ${size_bytes} bytes"
  echo "INSERT counts:"
  echo "  message_logs: ${message_logs_inserts}"
  echo "  service_heartbeats: ${service_heartbeats_inserts}"
  echo "  bot_health_checks: ${bot_health_checks_inserts}"
  exit 0
fi

echo "Unsupported DB_URL scheme: ${DB_URL}" >&2
exit 1
