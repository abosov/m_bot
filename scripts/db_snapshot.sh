#!/usr/bin/env bash
set -euo pipefail

DB_URL="${DB_URL:-}"
OUT_PATH=""
DAYS=""

usage() {
  cat <<'USAGE'
Usage: scripts/db_snapshot.sh [--out PATH] [--days N]

Before run on server, load env:
  source /etc/zumbot/backend.env

SQLite:
  Creates /tmp/zumbot_snapshot.db using sqlite3 .backup.

PostgreSQL:
  Creates /tmp/zumbot_logs_dump.sql using pg_dump (data-only for log tables).
  Use --days to dump only recent records.

The PostgreSQL dump is plain SQL for psql restore and intentionally uses:
  --no-owner --no-privileges --column-inserts --quote-all-identifiers
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

if [[ -z "${DB_URL}" ]]; then
  echo "DB_URL is not set. Example: source /etc/zumbot/backend.env && scripts/db_snapshot.sh" >&2
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

    pg_dump "${dump_opts[@]}" >> "${OUT_PATH}"
  }

  dump_table "message_logs" "created_at"
  dump_table "service_heartbeats" "ts"
  dump_table "bot_health_checks" "checked_at"

  echo "PostgreSQL logs dump written to ${OUT_PATH}"
  echo "Note: if your pg_dump adds \\unrestrict markers, they are psql metacommands from newer PostgreSQL clients and are safe when restoring with psql." 
  exit 0
fi

echo "Unsupported DB_URL scheme: ${DB_URL}" >&2
exit 1
