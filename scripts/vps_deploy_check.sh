#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/opt/zumbot/backend"
ENV_FILE="/etc/zumbot/backend.env"
VENV_DIR="${REPO_DIR}/.venv"
SERVICE_NAME="zumbot-backend.service"
SOCKET_NAME="zumbot-backend.socket"
LOCAL_HEALTH_URL="http://127.0.0.1:8000/healthz"
LOCAL_READYZ_URL="http://127.0.0.1:8000/readyz"
DOMAIN_BASE_URL="${ZUMBOT_DOMAIN_BASE_URL:-}"
VERBOSE="${VERBOSE:-0}"
RESULT="OK"

OK_COUNT=0
FAIL_COUNT=0

log_check() {
  local status="$1"
  local title="$2"
  local reason="$3"

  printf '[%s] %s - %s\n' "${status}" "${title}" "${reason}"

  if [[ "${status}" == "OK" ]]; then
    OK_COUNT=$((OK_COUNT + 1))
  else
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
}

print_verbose() {
  if [[ "${VERBOSE}" == "1" ]]; then
    printf '       %s\n' "$1"
  fi
}

check_git_clean() {
  local title="git clean"
  if [[ ! -d "${REPO_DIR}" ]]; then
    log_check "FAIL" "${title}" "repository not found (${REPO_DIR})"
    return
  fi

  if sudo -u zumbot bash -lc "cd '${REPO_DIR}' && git diff --quiet && git diff --cached --quiet" \
    && [[ -z "$(sudo -u zumbot bash -lc "cd '${REPO_DIR}' && git ls-files --others --exclude-standard")" ]]; then
    log_check "OK" "${title}" "working tree is clean"
  else
    log_check "FAIL" "${title}" "working tree has uncommitted/untracked changes"
    print_verbose "Run: sudo -u zumbot bash -lc 'cd ${REPO_DIR} && git status --short'"
  fi
}

check_venv_exists() {
  local title="venv exists"
  if [[ -x "${VENV_DIR}/bin/python" ]]; then
    log_check "OK" "${title}" "python executable found"
    print_verbose "python path: ${VENV_DIR}/bin/python"
    print_verbose "python version: $(sudo -u zumbot "${VENV_DIR}/bin/python" -V 2>&1 || true)"
  else
    log_check "FAIL" "${title}" "missing ${VENV_DIR}/bin/python"
  fi
}

check_pip_deps_installed() {
  local title="pip deps installed"
  if [[ ! -f "${REPO_DIR}/requirements.txt" ]]; then
    log_check "FAIL" "${title}" "requirements.txt is missing"
    return
  fi

  if sudo -u zumbot bash -lc "cd '${REPO_DIR}' && source '${VENV_DIR}/bin/activate' && pip check >/dev/null"; then
    log_check "OK" "${title}" "pip check passed"
    if [[ "${VERBOSE}" == "1" ]]; then
      local pip_version
      pip_version="$(sudo -u zumbot bash -lc "cd '${REPO_DIR}' && source '${VENV_DIR}/bin/activate' && pip --version" 2>/dev/null || true)"
      print_verbose "${pip_version}"
    fi
  else
    log_check "FAIL" "${title}" "dependency conflict or missing package"
    print_verbose "Run: sudo -u zumbot bash -lc 'cd ${REPO_DIR} && source ${VENV_DIR}/bin/activate && pip install -r requirements.txt && pip check'"
  fi
}

check_env_vars_present() {
  local title="env vars present"
  if [[ ! -f "${ENV_FILE}" ]]; then
    log_check "FAIL" "${title}" "env file not found (${ENV_FILE})"
    return
  fi

  set +u
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set -u

  local missing=()
  local required=(APP_ENV MASTER_BOT_TOKEN ENCRYPTION_KEY GOOGLE_CLIENT_ID GOOGLE_CLIENT_SECRET GOOGLE_REDIRECT_URI BASE_URL PUBLIC_SITE_URL DB_URL)
  local key
  for key in "${required[@]}"; do
    if [[ -z "${!key:-}" ]]; then
      missing+=("${key}")
    fi
  done

  if [[ ${#missing[@]} -eq 0 ]]; then
    log_check "OK" "${title}" "all required variables are set"
  else
    log_check "FAIL" "${title}" "missing: ${missing[*]}"
  fi

  if [[ "${VERBOSE}" == "1" ]]; then
    print_verbose "ENV_FILE=${ENV_FILE}"
    print_verbose "APP_ENV=${APP_ENV:-unset}, BASE_URL=${BASE_URL:-unset}"
  fi
}

check_postgres_reachable() {
  local title="postgres reachable"
  set +u
  # shellcheck disable=SC1090
  source "${ENV_FILE}" 2>/dev/null || true
  set -u

  if [[ -z "${DB_URL:-}" ]]; then
    log_check "FAIL" "${title}" "DB_URL is empty"
    return
  fi

  if [[ "${DB_URL}" != postgres* ]]; then
    log_check "OK" "${title}" "skipped (non-postgres DB_URL)"
    return
  fi

  if command -v pg_isready >/dev/null 2>&1 && pg_isready -d "${DB_URL/+asyncpg/}" >/dev/null 2>&1; then
    log_check "OK" "${title}" "pg_isready succeeded"
  else
    log_check "FAIL" "${title}" "pg_isready failed"
  fi
}

normalize_db_url_to_pg_dsn() {
  local raw_db_url="$1"
  local normalized

  if [[ "${raw_db_url}" == postgresql+asyncpg://* ]]; then
    normalized="postgresql://${raw_db_url#postgresql+asyncpg://}"
  elif [[ "${raw_db_url}" == postgres://* ]]; then
    normalized="postgresql://${raw_db_url#postgres://}"
  elif [[ "${raw_db_url}" == postgresql://* ]]; then
    normalized="${raw_db_url}"
  else
    echo "unsupported DB_URL scheme" >&2
    return 1
  fi

  local without_query="${normalized%%\?*}"
  local authority_and_path="${without_query#*://}"
  if [[ "${authority_and_path}" != */* ]]; then
    echo "DB_URL must include dbname path" >&2
    return 1
  fi

  local dbname="${authority_and_path#*/}"
  if [[ -z "${dbname}" ]]; then
    echo "DB_URL dbname is empty" >&2
    return 1
  fi

  printf '%s\n' "${normalized}"
}

run_sql_migrations() {
  local title="Run SQL migrations"
  local migrations_dir="${REPO_DIR}/scripts/migrations"

  if [[ ! -d "${migrations_dir}" ]]; then
    log_check "OK" "${title}" "skipped (no ${migrations_dir})"
    return
  fi

  set +u
  # shellcheck disable=SC1090
  source "${ENV_FILE}" 2>/dev/null || true
  set -u

  if [[ -z "${DB_URL:-}" ]]; then
    log_check "FAIL" "${title}" "DB_URL is empty"
    RESULT="FAIL"
    exit 1
  fi

  local pg_dsn
  if ! pg_dsn="$(normalize_db_url_to_pg_dsn "${DB_URL}")"; then
    log_check "FAIL" "${title}" "invalid DB_URL format (pgsql dbname is required)"
    RESULT="FAIL"
    exit 1
  fi

  if ! command -v psql >/dev/null 2>&1; then
    log_check "FAIL" "${title}" "psql is not installed"
    RESULT="FAIL"
    exit 1
  fi

  if ! sudo -u zumbot psql "${pg_dsn}" -v ON_ERROR_STOP=1 -tAc 'SELECT 1' >/dev/null; then
    log_check "FAIL" "${title}" "psql connection self-check failed"
    RESULT="FAIL"
    exit 1
  fi

  mapfile -t migration_files < <(find "${migrations_dir}" -maxdepth 1 -type f -name '*.sql' | sort)
  if [[ ${#migration_files[@]} -eq 0 ]]; then
    log_check "OK" "${title}" "no SQL migrations found"
    return
  fi

  local migration
  for migration in "${migration_files[@]}"; do
    if ! sudo -u zumbot psql "${pg_dsn}" -v ON_ERROR_STOP=1 -f "${migration}" >/dev/null; then
      log_check "FAIL" "${title}" "migration failed: $(basename "${migration}")"
      RESULT="FAIL"
      exit 1
    fi
  done

  log_check "OK" "${title}" "applied ${#migration_files[@]} SQL migration(s)"
}

check_http() {
  local url="$1"
  curl -fsS --max-time 5 "${url}" >/dev/null
}

check_healthz() {
  local title="/healthz"
  if check_http "${LOCAL_HEALTH_URL}"; then
    log_check "OK" "${title}" "endpoint returns 2xx"
  else
    log_check "FAIL" "${title}" "endpoint is unavailable"
    if [[ "${VERBOSE}" == "1" ]]; then
      print_verbose "Recent service logs:"
      journalctl -u "${SERVICE_NAME}" -n 20 --no-pager 2>/dev/null | sed 's/^/       /' || true
    fi
  fi
}

check_readyz() {
  local title="/readyz"
  if check_http "${LOCAL_READYZ_URL}"; then
    log_check "OK" "${title}" "endpoint returns 2xx"
  else
    log_check "FAIL" "${title}" "endpoint is unavailable"
    print_verbose "Verify DB connectivity and ENABLE_READYZ=true in ${ENV_FILE}"
  fi
}

check_nginx() {
  local title="nginx -t"
  if nginx -t >/dev/null 2>&1; then
    log_check "OK" "${title}" "configuration test passed"
  else
    log_check "FAIL" "${title}" "configuration test failed"
    print_verbose "Run: nginx -t"
  fi
}

check_socket_activation() {
  local title="socket activation"
  if systemctl is-enabled --quiet "${SOCKET_NAME}" \
    && systemctl is-active --quiet "${SOCKET_NAME}" \
    && systemctl is-active --quiet "${SERVICE_NAME}"; then
    log_check "OK" "${title}" "socket and service are active"
  else
    log_check "FAIL" "${title}" "socket/service is disabled or inactive"
    if [[ "${VERBOSE}" == "1" ]]; then
      print_verbose "socket state: $(systemctl is-active "${SOCKET_NAME}" 2>/dev/null || true)"
      print_verbose "service state: $(systemctl is-active "${SERVICE_NAME}" 2>/dev/null || true)"
    fi
  fi
}

check_external_endpoints() {
  local title="external /healthz and /readyz"
  if [[ -z "${DOMAIN_BASE_URL}" ]]; then
    return
  fi

  if check_http "${DOMAIN_BASE_URL%/}/healthz" && check_http "${DOMAIN_BASE_URL%/}/readyz"; then
    log_check "OK" "${title}" "public endpoints return 2xx"
  else
    log_check "FAIL" "${title}" "public endpoint check failed"
  fi
}

main() {
  if [[ "$(id -u)" -ne 0 ]]; then
    echo "This script must be run as root."
    echo "hint: sudo bash ${REPO_DIR}/scripts/vps_deploy_check.sh"
    exit 1
  fi

  echo "== zumbot deploy checks =="
  check_git_clean
  check_venv_exists
  check_pip_deps_installed
  check_env_vars_present
  check_postgres_reachable
  run_sql_migrations
  check_healthz
  check_readyz
  check_nginx
  check_socket_activation
  check_external_endpoints

  echo
  echo "SUMMARY: OK=${OK_COUNT} FAIL=${FAIL_COUNT}"
  if [[ ${FAIL_COUNT} -eq 0 && "${RESULT}" == "OK" ]]; then
    echo "EXIT_CODE=0"
    exit 0
  fi

  echo "EXIT_CODE=1"
  exit 1
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
