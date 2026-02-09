#!/usr/bin/env bash
set -euo pipefail

DB_URL="${DB_URL:-}"
if [[ -z "${DB_URL}" ]]; then
  echo "DB_URL is not set." >&2
  exit 1
fi

OUT_PATH=""
DAYS=""

usage() {
  cat <<'USAGE'
Usage: scripts/db_snapshot.sh [--out PATH] [--days N]

SQLite:
  Creates /tmp/zumbot_snapshot.db using sqlite3 .backup.

PostgreSQL:
  Creates /tmp/zumbot_logs_dump.sql using pg_dump (data-only for log tables).
  Use --days to dump only recent records.

Requires DB_URL and Postgres env vars (PGHOST/PGUSER/PGPASSWORD/PGDATABASE) or .pgpass.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --out)
      OUT_PATH="$2"
      shift 2
      ;;
    --days)
      DAYS="$2"
      shift 2
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
  echo "SQLite snapshot written to ${OUT_PATH}"
  exit 0
fi

if [[ "${DB_URL}" == postgres* ]]; then
  OUT_PATH="${OUT_PATH:-/tmp/zumbot_logs_dump.sql}"
  if ! command -v pg_dump >/dev/null 2>&1; then
    echo "pg_dump is required for postgres snapshots." >&2
    exit 1
  fi

  PG_DUMP_URL="${DB_URL/+asyncpg/}"
  : > "${OUT_PATH}"
  echo "-- Zumbot logs snapshot" >> "${OUT_PATH}"
  echo "-- Generated at $(date -u +"%Y-%m-%dT%H:%M:%SZ")" >> "${OUT_PATH}"

  dump_table() {
    local table_name="$1"
    local ts_column="$2"
    local where_clause=""
    if [[ -n "${DAYS}" ]]; then
      where_clause="${ts_column} >= (now() - interval '${DAYS} days')"
    fi
    if [[ -n "${where_clause}" ]]; then
      pg_dump --dbname="${PG_DUMP_URL}" --data-only --column-inserts \
        --table="${table_name}" --where="${where_clause}" >> "${OUT_PATH}"
    else
      pg_dump --dbname="${PG_DUMP_URL}" --data-only --column-inserts \
        --table="${table_name}" >> "${OUT_PATH}"
    fi
  }

  dump_table "message_logs" "created_at"
  dump_table "service_heartbeats" "ts"
  dump_table "bot_health_checks" "checked_at"

  echo "PostgreSQL logs dump written to ${OUT_PATH}"
  exit 0
fi

echo "Unsupported DB_URL scheme: ${DB_URL}" >&2
exit 1
