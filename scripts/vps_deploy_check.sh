#!/usr/bin/env bash
set -uo pipefail

REPO_DIR="/opt/zumbot/backend"
ENV_FILE="/etc/zumbot/backend.env"
VENV_DIR="${REPO_DIR}/.venv"
SERVICE_NAME="zumbot-backend.service"
SOCKET_NAME="zumbot-backend.socket"
LOCAL_HEALTH_URL="http://127.0.0.1:8000/healthz"
LOCAL_READYZ_URL="http://127.0.0.1:8000/readyz"
DOMAIN_BASE_URL="${ZUMBOT_DOMAIN_BASE_URL:-}"
LOG_PATH="/tmp/zumbot_deploy_$(date +"%Y%m%d_%H%M%S").log"
RESULT="OK"

mkdir -p /tmp
exec > >(tee -a "${LOG_PATH}") 2>&1

echo "== zumbot deploy+check started: $(date -u +"%Y-%m-%dT%H:%M:%SZ") =="
echo "Log: ${LOG_PATH}"

run_step() {
  local title="$1"
  shift
  echo
  echo "---- ${title} ----"
  if ! "$@"; then
    echo "[FAIL] ${title}"
    RESULT="FAIL"
    return 1
  fi
  echo "[OK] ${title}"
}

run_step_allow_fail() {
  local title="$1"
  shift
  echo
  echo "---- ${title} ----"
  if ! "$@"; then
    echo "[WARN] ${title}"
    RESULT="FAIL"
    return 1
  fi
  echo "[OK] ${title}"
}

run_in_repo_as_zumbot() {
  local cmd="$1"
  sudo -u zumbot bash -lc "cd '${REPO_DIR}' && ${cmd}"
}

require_paths() {
  [[ -d "${REPO_DIR}" ]] || { echo "Missing repo dir: ${REPO_DIR}"; return 1; }
  [[ -d "${VENV_DIR}" ]] || { echo "Missing venv dir: ${VENV_DIR}"; return 1; }
  [[ -f "${ENV_FILE}" ]] || { echo "Missing env file: ${ENV_FILE}"; return 1; }
}

run_git_update() {
  run_in_repo_as_zumbot "git fetch --all --prune"
  run_in_repo_as_zumbot "git pull --ff-only"
}

run_deps_install() {
  run_in_repo_as_zumbot "source '${VENV_DIR}/bin/activate' && pip install -r requirements.txt"
}

run_sql_migrations() {
  local migration
  shopt -s nullglob
  for migration in "${REPO_DIR}"/scripts/migrations/*.sql; do
    echo "Applying migration: ${migration}"
    sudo -u postgres psql -v ON_ERROR_STOP=1 "${DB_URL}" -f "${migration}"
  done
  shopt -u nullglob
}

reload_restart_service() {
  systemctl daemon-reload
  systemctl restart "${SERVICE_NAME}"
}

check_health() {
  curl -fsS "${LOCAL_HEALTH_URL}" >/dev/null
  curl -fsS "${LOCAL_READYZ_URL}" >/dev/null

  if [[ -n "${DOMAIN_BASE_URL}" ]]; then
    curl -fsS "${DOMAIN_BASE_URL%/}/healthz" >/dev/null
    curl -fsS "${DOMAIN_BASE_URL%/}/readyz" >/dev/null
  fi
}

run_pytest_test_env() {
  local test_key
  test_key="$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
  run_in_repo_as_zumbot "source '${VENV_DIR}/bin/activate' && APP_ENV=test ENCRYPTION_KEY='${test_key}' pytest"
}

collect_diagnostics() {
  systemctl status "${SERVICE_NAME}" --no-pager || true
  systemctl status "${SOCKET_NAME}" --no-pager || true
  journalctl -u "${SERVICE_NAME}" -n 300 --no-pager || true
  nginx -t || true

  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  run_in_repo_as_zumbot "source '${VENV_DIR}/bin/activate' && DB_URL='${DB_URL}' bash scripts/db_snapshot.sh"
}

if [[ "$(id -u)" -ne 0 ]]; then
  echo "This script must be run as root (it uses systemctl/journalctl/nginx and sudo -u zumbot)."
  RESULT="FAIL"
  echo "RESULT=${RESULT}"
  echo "LOG_PATH=${LOG_PATH}"
  exit 1
fi

run_step "Validate expected paths" require_paths || true

if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
fi

run_step "Git fetch/pull" run_git_update || true
run_step "Install Python dependencies" run_deps_install || true
run_step "Run SQL migrations" run_sql_migrations || true
run_step "Reload and restart systemd service" reload_restart_service || true
run_step "Health checks" check_health || true
run_step "Pytest in test env" run_pytest_test_env || true
run_step_allow_fail "Collect diagnostics" collect_diagnostics || true

echo
if [[ "${RESULT}" == "OK" ]]; then
  echo "RESULT=OK"
else
  echo "RESULT=FAIL"
fi
echo "LOG_PATH=${LOG_PATH}"
