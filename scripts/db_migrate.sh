#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
MIGRATIONS_DIR="${SCRIPT_DIR}/migrations"
ENV_FILE="/etc/zumbot/backend.env"

load_env_if_needed() {
  if [[ -n "${DB_URL:-}" ]]; then
    return 0
  fi

  if [[ -f "${ENV_FILE}" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${ENV_FILE}"
    set +a
  fi
}

ensure_vps_runtime() {
  if [[ "$(uname -s)" != "Linux" ]]; then
    echo "This script can run only on VPS (Linux + systemd host)." >&2
    exit 1
  fi

  if [[ ! -r /proc/1/comm ]] || [[ "$(cat /proc/1/comm 2>/dev/null)" != "systemd" ]]; then
    echo "This script can run only on VPS (systemd host required)." >&2
    exit 1
  fi

  if [[ -f /.dockerenv ]] || grep -qaE '(docker|containerd|kubepods|lxc)' /proc/1/cgroup 2>/dev/null; then
    echo "This script can run only on VPS (container runtime detected)." >&2
    exit 1
  fi
}

build_psql_url() {
  local db_url="$1"
  db_url="${db_url/postgresql+asyncpg:/postgresql:}"
  db_url="${db_url/postgres+asyncpg:/postgres:}"
  if [[ "${db_url}" == postgres://* ]]; then
    db_url="postgresql://${db_url#postgres://}"
  fi
  printf '%s\n' "${db_url}"
}

sql_escape_literal() {
  printf '%s' "$1" | sed "s/'/''/g"
}

ensure_requirements() {
  command -v psql >/dev/null 2>&1 || { echo "psql is required" >&2; exit 1; }
  command -v sha256sum >/dev/null 2>&1 || { echo "sha256sum is required" >&2; exit 1; }
  [[ -n "${DB_URL:-}" ]] || {
    echo "DB_URL is required. Export DB_URL or define it in ${ENV_FILE}" >&2
    exit 1
  }
}

apply_migrations() {
  local psql_url migration_file filename sha current_sha filename_escaped

  psql_url="$(build_psql_url "${DB_URL}")"

  psql -v ON_ERROR_STOP=1 "${psql_url}" -c "CREATE TABLE IF NOT EXISTS schema_migrations (filename text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now(), sha256 text NOT NULL);" >/dev/null

  shopt -s nullglob
  local files=("${MIGRATIONS_DIR}"/*.sql)
  shopt -u nullglob

  if [[ ${#files[@]} -eq 0 ]]; then
    echo "No migrations found"
    exit 0
  fi

  mapfile -t files < <(printf '%s\n' "${files[@]}" | sort)

  for migration_file in "${files[@]}"; do
    filename="$(basename "${migration_file}")"
    sha="$(sha256sum "${migration_file}" | awk '{print $1}')"
    filename_escaped="$(sql_escape_literal "${filename}")"

    current_sha="$(psql -v ON_ERROR_STOP=1 -At "${psql_url}" -c "SELECT sha256 FROM schema_migrations WHERE filename = '${filename_escaped}';")"

    if [[ -n "${current_sha}" ]]; then
      if [[ "${current_sha}" == "${sha}" ]]; then
        echo "Skipping ${filename} (already applied)"
        continue
      fi

      echo "Checksum mismatch for migration ${filename}. Existing=${current_sha}, New=${sha}" >&2
      exit 1
    fi

    echo "Applying ${filename}"
    psql -v ON_ERROR_STOP=1 "${psql_url}" -f "${migration_file}"
    psql -v ON_ERROR_STOP=1 "${psql_url}" -c "INSERT INTO schema_migrations(filename, sha256) VALUES ('${filename_escaped}', '${sha}');" >/dev/null
  done
}

main() {
  ensure_vps_runtime
  load_env_if_needed
  ensure_requirements
  apply_migrations
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
