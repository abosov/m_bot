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
MODE="checks"
RESULT="OK"
EXIT_CODE=0
LOG_PATH="${LOG_PATH:-/tmp/zumbot_deploy_check_$(date -u +%Y%m%dT%H%M%SZ).log}"
CURRENT_STEP="init"
SUMMARY_PRINTED=0

OK_COUNT=0
FAIL_COUNT=0

usage() {
  cat <<USAGE
Usage:
  $(basename "$0") [--mode deploy|checks] [--verbose]

Modes:
  deploy   Full deployment flow:
           git pull + pip install + SQL migrations + service restart + health checks.
  checks   Checks only (default). No git pull, no pip install, no migrations, no restart.

Examples:
  sudo VERBOSE=1 bash ${REPO_DIR}/scripts/vps_deploy_check.sh --mode deploy
  bash ${REPO_DIR}/scripts/vps_deploy_check.sh --mode checks
USAGE
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --mode)
        MODE="$2"
        shift 2
        ;;
      --verbose)
        VERBOSE=1
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        echo "Unknown argument: $1" >&2
        usage
        exit 2
        ;;
    esac
  done

  if [[ "${MODE}" != "deploy" && "${MODE}" != "checks" ]]; then
    echo "Invalid --mode: ${MODE}. Use deploy|checks." >&2
    exit 2
  fi
}

setup_logging() {
  if [[ "${DEPLOY_CHECK_LOGGING_READY:-0}" == "1" ]]; then
    return
  fi

  export DEPLOY_CHECK_LOGGING_READY=1
  mkdir -p "$(dirname "${LOG_PATH}")"
  touch "${LOG_PATH}"
  exec > >(tee -a "${LOG_PATH}") 2>&1
}

run_as_zumbot() {
  if [[ "$(id -un)" == "zumbot" ]]; then
    "$@"
    return
  fi

  if [[ "$(id -u)" -eq 0 ]]; then
    sudo -u zumbot "$@"
  else
    sudo -u zumbot "$@"
  fi
}

run_as_root() {
  if [[ "$(id -u)" -eq 0 ]]; then
    "$@"
  else
    sudo "$@"
  fi
}

mask_url() {
  local raw_url="$1"
  echo "${raw_url}" | sed -E 's#(://[^:/@]+:)[^@/]*(\@)#\1***\2#'
}

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

print_final_status() {
  if [[ "${SUMMARY_PRINTED}" == "1" ]]; then
    return
  fi

  SUMMARY_PRINTED=1
  echo
  echo "SUMMARY: OK=${OK_COUNT} FAIL=${FAIL_COUNT}"
  echo "RESULT=${RESULT}"
  echo "LOG_PATH=${LOG_PATH}"
}

on_exit() {
  local exit_code=$?
  if [[ ${exit_code} -ne 0 ]]; then
    RESULT="FAIL"
    EXIT_CODE=1
    echo "FAILED_STEP=${CURRENT_STEP}"
  fi
  print_final_status
}

run_step() {
  local step_name="$1"
  shift
  CURRENT_STEP="${step_name}"
  "$@"
}

check_git_clean() {
  local title="git clean"
  if [[ ! -d "${REPO_DIR}" ]]; then
    log_check "FAIL" "${title}" "repository not found (${REPO_DIR})"
    return
  fi

  if run_as_zumbot bash -lc "cd '${REPO_DIR}' && git diff --quiet && git diff --cached --quiet" \
    && [[ -z "$(run_as_zumbot bash -lc "cd '${REPO_DIR}' && git ls-files --others --exclude-standard")" ]]; then
    log_check "OK" "${title}" "working tree is clean"
  else
    log_check "FAIL" "${title}" "working tree has uncommitted/untracked changes"
    print_verbose "Run: sudo -u zumbot bash -lc 'cd ${REPO_DIR} && git status --short'"
  fi
}

update_repo() {
  local title="git pull"
  if [[ "${MODE}" == "checks" ]]; then
    log_check "OK" "${title}" "skipped in checks mode"
    return
  fi

  if run_as_zumbot bash -lc "cd '${REPO_DIR}' && git pull --ff-only"; then
    log_check "OK" "${title}" "repository updated"
  else
    log_check "FAIL" "${title}" "git pull --ff-only failed"
    RESULT="FAIL"
    exit 1
  fi
}

check_venv_exists() {
  local title="venv exists"
  if [[ -x "${VENV_DIR}/bin/python" ]]; then
    log_check "OK" "${title}" "python executable found"
    print_verbose "python path: ${VENV_DIR}/bin/python"
    print_verbose "python version: $(run_as_zumbot "${VENV_DIR}/bin/python" -V 2>&1 || true)"
  else
    log_check "FAIL" "${title}" "missing ${VENV_DIR}/bin/python"
  fi
}

install_pip_deps() {
  local title="pip install"
  if [[ "${MODE}" == "checks" ]]; then
    log_check "OK" "${title}" "skipped in checks mode"
    return
  fi

  if [[ ! -f "${REPO_DIR}/requirements.txt" ]]; then
    log_check "FAIL" "${title}" "requirements.txt is missing"
    RESULT="FAIL"
    exit 1
  fi

  if run_as_zumbot bash -lc "cd '${REPO_DIR}' && source '${VENV_DIR}/bin/activate' && pip install -r requirements.txt"; then
    log_check "OK" "${title}" "dependencies installed"
  else
    log_check "FAIL" "${title}" "pip install failed"
    RESULT="FAIL"
    exit 1
  fi
}

check_pip_deps_installed() {
  local title="pip deps installed"
  if [[ ! -f "${REPO_DIR}/requirements.txt" ]]; then
    log_check "FAIL" "${title}" "requirements.txt is missing"
    return
  fi

  if run_as_zumbot bash -lc "cd '${REPO_DIR}' && source '${VENV_DIR}/bin/activate' && pip check >/dev/null"; then
    log_check "OK" "${title}" "pip check passed"
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

  local psql_url
  psql_url="$(build_psql_url "${DB_URL}")"
  if command -v pg_isready >/dev/null 2>&1 && pg_isready -d "${psql_url}" >/dev/null 2>&1; then
    log_check "OK" "${title}" "pg_isready succeeded"
  else
    log_check "FAIL" "${title}" "pg_isready failed"
  fi
}

validate_psql_url() {
  local raw_url="$1"
  local without_query authority_and_path dbname

  if [[ "${raw_url}" != postgres://* && "${raw_url}" != postgresql://* ]]; then
    echo "unsupported DB_URL scheme" >&2
    return 1
  fi

  without_query="${raw_url%%\?*}"
  authority_and_path="${without_query#*://}"
  if [[ "${authority_and_path}" != */* ]]; then
    echo "DB_URL must include dbname path" >&2
    return 1
  fi

  dbname="${authority_and_path#*/}"
  if [[ -z "${dbname}" ]]; then
    echo "DB_URL dbname is empty" >&2
    return 1
  fi
}

run_psql() {
  local psql_url="$1"
  shift
  run_as_zumbot psql "${psql_url}" -v ON_ERROR_STOP=1 "$@"
}

build_psql_url() {
  local db_url="$1"
  local psql_url

  psql_url="${db_url/postgresql+asyncpg:/postgresql:}"
  psql_url="${psql_url/postgres+asyncpg:/postgres:}"
  if [[ "${psql_url}" == postgres://* ]]; then
    psql_url="postgresql://${psql_url#postgres://}"
  fi

  echo "${psql_url}"
}

run_sql_migrations() {
  local title="Run SQL migrations"
  local migrations_dir="${REPO_DIR}/scripts/migrations"

  if [[ "${MODE}" == "checks" ]]; then
    log_check "OK" "${title}" "skipped in checks mode"
    return
  fi

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

  local PSQL_URL
  PSQL_URL="$(build_psql_url "${DB_URL}")"
  print_verbose "Using psql URL: $(mask_url "${PSQL_URL}")"

  if ! validate_psql_url "${PSQL_URL}"; then
    log_check "FAIL" "${title}" "invalid DB_URL format (pgsql dbname is required)"
    RESULT="FAIL"
    exit 1
  fi

  if ! command -v psql >/dev/null 2>&1; then
    log_check "FAIL" "${title}" "psql is not installed"
    RESULT="FAIL"
    exit 1
  fi

  if ! run_psql "${PSQL_URL}" -tAc 'SELECT 1' >/dev/null; then
    log_check "FAIL" "${title}" "psql connection self-check failed"
    RESULT="FAIL"
    exit 1
  fi

  if ! run_psql "${PSQL_URL}" -c "CREATE TABLE IF NOT EXISTS applied_migrations (id BIGSERIAL PRIMARY KEY, filename TEXT UNIQUE NOT NULL, applied_at TIMESTAMPTZ NOT NULL DEFAULT now());" >/dev/null; then
    log_check "FAIL" "${title}" "failed to ensure applied_migrations table"
    RESULT="FAIL"
    exit 1
  fi

  mapfile -t migration_files < <(find "${migrations_dir}" -maxdepth 1 -type f -name '*.sql' | sort)
  if [[ ${#migration_files[@]} -eq 0 ]]; then
    log_check "OK" "${title}" "no SQL migrations found"
    return
  fi

  local migration
  local applied_count=0
  local skipped_count=0
  local migration_exit_code=0
  local migration_state=""
  for migration in "${migration_files[@]}"; do
    local migration_basename
    migration_basename="$(basename "${migration}")"

    migration_state="applied"
    if run_psql "${PSQL_URL}" -tAc "SELECT 1 FROM applied_migrations WHERE filename = '${migration_basename}' LIMIT 1;" | grep -q '1'; then
      migration_state="skipped (already applied)"
      skipped_count=$((skipped_count + 1))
      echo "[MIGRATION] ${migration_basename}: ${migration_state}"
      continue
    fi

    if run_psql "${PSQL_URL}" -f "${migration}" >/dev/null 2>&1; then
      :
    else
      migration_exit_code=$?
      echo "[MIGRATION] ${migration_basename}: failed (exit_code=${migration_exit_code})"
      log_check "FAIL" "${title}" "migration failed: ${migration_basename}"
      RESULT="FAIL"
      EXIT_CODE=1
      exit 1
    fi

    if ! run_psql "${PSQL_URL}" -c "INSERT INTO applied_migrations(filename) VALUES ('${migration_basename}') ON CONFLICT (filename) DO NOTHING;" >/dev/null; then
      log_check "FAIL" "${title}" "failed to record applied migration: ${migration_basename}"
      RESULT="FAIL"
      EXIT_CODE=1
      exit 1
    fi

    echo "[MIGRATION] ${migration_basename}: applied"
    applied_count=$((applied_count + 1))
  done

  log_check "OK" "${title}" "applied=${applied_count} skipped=${skipped_count} total=${#migration_files[@]}"
}

check_http() {
  local url="$1"
  local http_code
  http_code="$(curl -sS --max-time 5 -o /dev/null -w '%{http_code}' "${url}")"
  [[ "${http_code}" == "200" ]]
}

restart_backend_service() {
  local title="restart backend service"
  if [[ "${MODE}" == "checks" ]]; then
    log_check "OK" "${title}" "skipped in checks mode"
    return
  fi

  if run_as_root systemctl restart "${SERVICE_NAME}"; then
    log_check "OK" "${title}" "service restarted"
  else
    log_check "FAIL" "${title}" "systemctl restart failed"
    RESULT="FAIL"
    exit 1
  fi
}

check_healthz() {
  local title="/healthz"
  if check_http "${LOCAL_HEALTH_URL}"; then
    log_check "OK" "${title}" "endpoint returns HTTP 200"
  else
    log_check "FAIL" "${title}" "endpoint is unavailable"
  fi
}

check_readyz() {
  local title="/readyz"
  if check_http "${LOCAL_READYZ_URL}"; then
    log_check "OK" "${title}" "endpoint returns HTTP 200"
  else
    log_check "FAIL" "${title}" "endpoint is unavailable"
    print_verbose "Verify DB connectivity and ENABLE_READYZ=true in ${ENV_FILE}"
  fi
}

check_nginx() {
  local title="nginx -t"
  if run_as_root nginx -t >/dev/null 2>&1; then
    log_check "OK" "${title}" "configuration test passed"
  else
    log_check "FAIL" "${title}" "configuration test failed"
  fi
}

check_socket_activation() {
  local title="socket activation"
  if run_as_root systemctl is-enabled --quiet "${SOCKET_NAME}" \
    && run_as_root systemctl is-active --quiet "${SOCKET_NAME}" \
    && run_as_root systemctl is-active --quiet "${SERVICE_NAME}"; then
    log_check "OK" "${title}" "socket and service are active"
  else
    log_check "FAIL" "${title}" "socket/service is disabled or inactive"
  fi
}

check_external_endpoints() {
  local title="external /healthz and /readyz"
  if [[ -z "${DOMAIN_BASE_URL}" ]]; then
    return
  fi

  if check_http "${DOMAIN_BASE_URL%/}/healthz" && check_http "${DOMAIN_BASE_URL%/}/readyz"; then
    log_check "OK" "${title}" "public endpoints return HTTP 200"
  else
    log_check "FAIL" "${title}" "public endpoint check failed"
  fi
}

main() {
  parse_args "$@"
  setup_logging
  trap on_exit EXIT

  echo "== zumbot deploy checks (mode=${MODE}) =="
  run_step "git clean" check_git_clean
  run_step "git pull" update_repo
  run_step "venv exists" check_venv_exists
  run_step "pip install" install_pip_deps
  run_step "pip deps installed" check_pip_deps_installed
  run_step "env vars present" check_env_vars_present
  run_step "postgres reachable" check_postgres_reachable
  run_step "run sql migrations" run_sql_migrations
  run_step "restart backend service" restart_backend_service
  run_step "check /healthz" check_healthz
  run_step "check /readyz" check_readyz
  run_step "nginx -t" check_nginx
  run_step "socket activation" check_socket_activation
  run_step "external endpoints" check_external_endpoints

  if [[ ${FAIL_COUNT} -eq 0 && "${RESULT}" == "OK" ]]; then
    RESULT="OK"
  else
    RESULT="FAIL"
  fi

  if [[ "${RESULT}" == "OK" ]]; then
    EXIT_CODE=0
  else
    EXIT_CODE=1
  fi

  exit "${EXIT_CODE}"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
