#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="/etc/zumbot/backend.env"
DB_MIGRATE_SCRIPT="${SCRIPT_DIR}/db_migrate.sh"
VENV_PYTHON="${REPO_ROOT}/.venv/bin/python3"

log() {
  printf '[run_migrations] %s\n' "$*"
}

load_env_if_needed() {
  if [[ -n "${DB_URL:-}" ]]; then
    return 0
  fi

  if [[ -f "${ENV_FILE}" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${ENV_FILE}"
    set +a
    log "loaded env from ${ENV_FILE}"
  fi
}

run_existing_migration_script() {
  log "running existing migration script: ${DB_MIGRATE_SCRIPT}"
  if bash "${DB_MIGRATE_SCRIPT}"; then
    log "OK: migrations applied"
    return 0
  else
    local rc=$?
    log "FAIL: migration script failed with exit code ${rc}"
    return "${rc}"
  fi
}

run_alembic_fallback() {
  local python_bin="python3"
  if [[ -x "${VENV_PYTHON}" ]]; then
    python_bin="${VENV_PYTHON}"
  fi

  load_env_if_needed

  if [[ -z "${DB_URL:-}" ]]; then
    log "FAIL: DB_URL is not set (env or ${ENV_FILE})"
    return 1
  fi

  if [[ ! -f "${REPO_ROOT}/alembic.ini" ]]; then
    log "FAIL: no alembic.ini found for fallback"
    return 1
  fi

  log "running alembic fallback via ${python_bin}"
  if (cd "${REPO_ROOT}" && "${python_bin}" -m alembic upgrade head); then
    log "OK: alembic upgrade head completed"
    return 0
  else
    local rc=$?
    log "FAIL: alembic upgrade head failed with exit code ${rc}"
    return "${rc}"
  fi
}

main() {
  if [[ -f "${DB_MIGRATE_SCRIPT}" ]]; then
    run_existing_migration_script
    return $?
  fi

  run_alembic_fallback
}

main "$@"
