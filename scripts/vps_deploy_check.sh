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

FAIL_COUNT=0

ok() {
  echo "[OK] $1"
}

fail() {
  local title="$1"
  local hint="$2"
  echo "[FAIL] ${title}"
  echo "       hint: ${hint}"
  FAIL_COUNT=$((FAIL_COUNT + 1))
}

check_git_clean() {
  local title="git clean"
  if [[ ! -d "${REPO_DIR}" ]]; then
    fail "${title}" "Repository not found: ${REPO_DIR}. Clone repo and set correct path."
    return
  fi

  if sudo -u zumbot bash -lc "cd '${REPO_DIR}' && git diff --quiet && git diff --cached --quiet" \
    && [[ -z "$(sudo -u zumbot bash -lc "cd '${REPO_DIR}' && git ls-files --others --exclude-standard")" ]]; then
    ok "${title}"
  else
    fail "${title}" "Working tree is dirty. Commit/stash/remove local changes before deploy."
  fi
}

check_venv_exists() {
  local title="venv exists"
  if [[ -x "${VENV_DIR}/bin/python" ]]; then
    ok "${title}"
  else
    fail "${title}" "Create venv: sudo -u zumbot python3 -m venv ${VENV_DIR}."
  fi
}

check_pip_deps_installed() {
  local title="pip deps installed"
  if [[ ! -f "${REPO_DIR}/requirements.txt" ]]; then
    fail "${title}" "Missing requirements.txt in ${REPO_DIR}."
    return
  fi

  if sudo -u zumbot bash -lc "cd '${REPO_DIR}' && source '${VENV_DIR}/bin/activate' && pip install -r requirements.txt >/dev/null && pip check >/dev/null"; then
    ok "${title}"
  else
    fail "${title}" "Install deps: sudo -u zumbot bash -lc 'cd ${REPO_DIR} && source ${VENV_DIR}/bin/activate && pip install -r requirements.txt'."
  fi
}

check_env_vars_present() {
  local title="env vars present"
  if [[ ! -f "${ENV_FILE}" ]]; then
    fail "${title}" "Create ${ENV_FILE} with required production variables."
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
    ok "${title}"
  else
    fail "${title}" "Set missing vars in ${ENV_FILE}: ${missing[*]}."
  fi
}

check_postgres_reachable() {
  local title="postgres reachable"
  set +u
  # shellcheck disable=SC1090
  source "${ENV_FILE}" 2>/dev/null || true
  set -u

  if [[ -z "${DB_URL:-}" ]]; then
    fail "${title}" "DB_URL is empty in ${ENV_FILE}."
    return
  fi

  if [[ "${DB_URL}" != postgres* ]]; then
    ok "${title} (skipped: non-postgres DB_URL)"
    return
  fi

  if command -v pg_isready >/dev/null 2>&1 && pg_isready -d "${DB_URL/+asyncpg/}" >/dev/null 2>&1; then
    ok "${title}"
  else
    fail "${title}" "Check DB_URL, network/firewall, postgres service, and credentials."
  fi
}

check_http() {
  local url="$1"
  curl -fsS --max-time 5 "${url}" >/dev/null
}

check_healthz() {
  local title="/healthz"
  if check_http "${LOCAL_HEALTH_URL}"; then
    ok "${title}"
  else
    fail "${title}" "Restart service and inspect logs: systemctl restart ${SERVICE_NAME}; journalctl -u ${SERVICE_NAME} -n 200 --no-pager."
  fi
}

check_readyz() {
  local title="/readyz"
  if check_http "${LOCAL_READYZ_URL}"; then
    ok "${title}"
  else
    fail "${title}" "Verify DB connectivity and ENABLE_READYZ=true in ${ENV_FILE}, then restart service."
  fi
}

check_nginx() {
  local title="nginx -t"
  if nginx -t >/dev/null 2>&1; then
    ok "${title}"
  else
    fail "${title}" "Fix nginx config and re-run: nginx -t."
  fi
}

check_socket_activation() {
  local title="socket activation"
  if systemctl is-enabled --quiet "${SOCKET_NAME}" \
    && systemctl is-active --quiet "${SOCKET_NAME}" \
    && systemctl is-active --quiet "${SERVICE_NAME}"; then
    ok "${title}"
  else
    fail "${title}" "Enable/start units: systemctl enable --now ${SOCKET_NAME} ${SERVICE_NAME}."
  fi
}

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
check_healthz
check_readyz
check_nginx
check_socket_activation

if [[ -n "${DOMAIN_BASE_URL}" ]]; then
  if check_http "${DOMAIN_BASE_URL%/}/healthz" && check_http "${DOMAIN_BASE_URL%/}/readyz"; then
    ok "external /healthz and /readyz"
  else
    fail "external /healthz and /readyz" "Check DNS/nginx upstream and TLS certs for ${DOMAIN_BASE_URL}."
  fi
fi

echo
if [[ ${FAIL_COUNT} -eq 0 ]]; then
  echo "RESULT=OK"
  exit 0
fi

echo "RESULT=FAIL (${FAIL_COUNT} checks failed)"
exit 1
