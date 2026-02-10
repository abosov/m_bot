#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="/etc/zumbot/backend.env"
VENV_DIR="${REPO_DIR}/.venv"
SERVICE_NAME="zumbot-backend.service"
SOCKET_NAME="zumbot-backend.socket"
LOG_PATH="${LOG_PATH:-/tmp/zumbot_deploy_check_$(date -u +%Y%m%dT%H%M%SZ).log}"

FAIL_COUNT=0

log() {
  echo "$*"
}

pass() {
  log "[OK] $1"
}

fail() {
  log "[FAIL] $1"
  FAIL_COUNT=$((FAIL_COUNT + 1))
}

check_cmd() {
  command -v "$1" >/dev/null 2>&1 || { fail "missing command: $1"; return 1; }
}

check_env_file() {
  if [[ -f "${ENV_FILE}" ]]; then
    pass "env file exists (${ENV_FILE})"
  else
    fail "env file not found (${ENV_FILE})"
  fi
}

check_repo() {
  if [[ -d "${REPO_DIR}/.git" ]]; then
    pass "repository exists (${REPO_DIR})"
  else
    fail "repository not found (${REPO_DIR})"
  fi
}

check_venv() {
  if [[ -x "${VENV_DIR}/bin/python" ]]; then
    pass "venv python exists"
  else
    fail "venv python missing (${VENV_DIR}/bin/python)"
  fi
}

check_systemd_units() {
  if systemctl is-enabled --quiet "${SERVICE_NAME}" && systemctl is-active --quiet "${SERVICE_NAME}"; then
    pass "${SERVICE_NAME} is enabled and active"
  else
    fail "${SERVICE_NAME} is not enabled/active"
  fi

  if systemctl is-enabled --quiet "${SOCKET_NAME}" && systemctl is-active --quiet "${SOCKET_NAME}"; then
    pass "${SOCKET_NAME} is enabled and active"
  else
    fail "${SOCKET_NAME} is not enabled/active"
  fi
}

check_http_endpoint() {
  local url="$1"
  local name="$2"

  if curl -fsS --max-time 5 "${url}" >/dev/null; then
    pass "${name} is reachable"
  else
    fail "${name} is unavailable (${url})"
  fi
}

check_nginx() {
  if nginx -t >/dev/null 2>&1; then
    pass "nginx -t passed"
  else
    fail "nginx -t failed"
  fi
}

check_migrations_read_only() {
  local migrations_dir="${REPO_DIR}/scripts/migrations"
  if [[ ! -d "${migrations_dir}" ]]; then
    pass "migrations directory not found (allowed): ${migrations_dir}"
    return
  fi

  local sql_count
  sql_count="$(find "${migrations_dir}" -maxdepth 1 -type f -name '*.sql' | wc -l | tr -d ' ')"
  pass "migrations directory exists, sql files=${sql_count} (read-only check)"
}

main() {
  exec > >(tee -a "${LOG_PATH}") 2>&1

  log "== zumbot deploy checks only =="

  if [[ "$(id -u)" -ne 0 ]]; then
    fail "run as root for full checks"
    log "LOG_PATH=${LOG_PATH}"
    exit 1
  fi

  check_cmd systemctl || true
  check_cmd curl || true
  check_cmd nginx || true
  check_repo
  check_env_file
  check_venv
  check_systemd_units
  check_http_endpoint "http://127.0.0.1:8000/healthz" "/healthz"
  check_http_endpoint "http://127.0.0.1:8000/readyz" "/readyz"
  check_nginx
  check_migrations_read_only

  if [[ ${FAIL_COUNT} -ne 0 ]]; then
    log "RESULT=FAIL"
    log "LOG_PATH=${LOG_PATH}"
    exit 1
  fi

  log "RESULT=OK"
  log "LOG_PATH=${LOG_PATH}"
}

main "$@"
