#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/opt/zumbot/backend"
ENV_FILE="/etc/zumbot/backend.env"
SERVICE_NAME="zumbot-backend.service"
CHECK_SCRIPT="${REPO_DIR}/scripts/vps_deploy_check.sh"
MIGRATE_SCRIPT="${REPO_DIR}/scripts/db_migrate.sh"
LOG_PATH="/tmp/zumbot_deploy_$(date -u +%Y%m%dT%H%M%SZ).log"

print_log_path() {
  echo "Deploy log: ${LOG_PATH}"
}

on_exit() {
  local rc=$?
  if [[ ${rc} -eq 0 ]]; then
    echo "Deploy finished successfully"
  else
    echo "Deploy failed"
  fi
  print_log_path
}

wait_readyz() {
  local attempts=30
  local url="http://127.0.0.1:8000/readyz"

  for ((i=1; i<=attempts; i++)); do
    if curl -fsS --max-time 3 "${url}" >/dev/null; then
      echo "readyz is OK"
      return 0
    fi
    sleep 1
  done

  echo "readyz check failed after ${attempts}s" >&2
  return 1
}

main() {
  trap on_exit EXIT
  exec > >(tee -a "${LOG_PATH}") 2>&1

  if [[ "$(id -u)" -ne 0 ]]; then
    echo "This script must be run as root (needs systemctl/nginx/journalctl access)." >&2
    exit 1
  fi

  cd "${REPO_DIR}"

  git fetch origin
  git pull --ff-only origin main

  sudo -u zumbot bash -lc "cd '${REPO_DIR}' && source .venv/bin/activate && pip install -r requirements.txt"

  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a

  bash "${MIGRATE_SCRIPT}"

  systemctl restart "${SERVICE_NAME}"
  wait_readyz

  bash "${CHECK_SCRIPT}"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
