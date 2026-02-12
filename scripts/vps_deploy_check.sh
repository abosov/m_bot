#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="/etc/zumbot/backend.env"
VENV_DIR="${REPO_DIR}/.venv"
SERVICE_NAME="zumbot-backend.service"
SOCKET_NAME="zumbot-backend.socket"
MIGRATE_SCRIPT="${REPO_DIR}/scripts/db_migrate.sh"
MODE="checks"
LOG_PATH="/tmp/zumbot_deploy_$(date +%Y%m%d_%H%M%S).log"
APP_BASE_URL="http://127.0.0.1:8000"
VERSION_FILE="${REPO_DIR}/VERSION"

normalize_db_url() {
  local db_url="$1"
  db_url="${db_url/postgresql+asyncpg:/postgresql:}"
  db_url="${db_url/postgres+asyncpg:/postgres:}"
  if [[ "${db_url}" == postgres://* ]]; then
    db_url="postgresql://${db_url#postgres://}"
  fi
  printf '%s\n' "${db_url}"
}

log() {
  echo "$*"
}

pass() {
  log "[OK] $1"
}

die() {
  log "[FAIL] $1"
  exit 1
}

run_step() {
  local name="$1"
  shift

  log "== ${name} =="
  "$@"
  pass "${name}"
}


print_git_and_build_info() {
  local git_head build_number
  git_head="$(git -C "${REPO_DIR}" log -1 --pretty=format:'%h %s')"
  build_number="unknown"
  if [[ -f "${VERSION_FILE}" ]]; then
    build_number="$(tr -d '[:space:]' < "${VERSION_FILE}")"
  fi
  log "[INFO] git HEAD: ${git_head}"
  log "[INFO] build number: ${build_number}"
}

check_yaml_import() {
  sudo -u zumbot bash -lc "cd '${REPO_DIR}' && source .venv/bin/activate && python -c 'import yaml; print("PyYAML OK")'" >/dev/null     || die "PyYAML import failed in .venv. Install deps (pip install -r requirements.txt) and verify requirements include PyYAML."
}

check_migrations_applied() {
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a

  [[ -n "${DB_URL:-}" ]] || die "DB_URL is required in ${ENV_FILE}"
  local db_url_for_cli
  db_url_for_cli="$(normalize_db_url "${DB_URL}")"
  env DB_URL="${db_url_for_cli}" bash "${MIGRATE_SCRIPT}" || die "Migration check/apply failed"
}

check_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "missing command: $1"
}

check_env_file() {
  [[ -f "${ENV_FILE}" ]] || die "env file not found (${ENV_FILE})"
}

check_repo() {
  [[ -d "${REPO_DIR}/.git" ]] || die "repository not found (${REPO_DIR})"
}

check_venv() {
  [[ -x "${VENV_DIR}/bin/python" ]] || die "venv python missing (${VENV_DIR}/bin/python)"
}

check_systemd_units() {
  systemctl is-enabled --quiet "${SERVICE_NAME}" || die "${SERVICE_NAME} is not enabled"
  systemctl is-active --quiet "${SERVICE_NAME}" || die "${SERVICE_NAME} is not active"
  systemctl is-enabled --quiet "${SOCKET_NAME}" || die "${SOCKET_NAME} is not enabled"
  systemctl is-active --quiet "${SOCKET_NAME}" || die "${SOCKET_NAME} is not active"
}

check_http_endpoint() {
  local url="$1"
  local name="$2"
  local code

  code="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 2 --max-time 5 "${url}")" || {
    die "${name} is unavailable (${url})"
  }

  [[ "${code}" == "200" ]] || die "${name} returned HTTP ${code}, expected 200 (${url})"
}

check_nginx() {
  nginx -t >/dev/null 2>&1 || die "nginx -t failed"
}

check_migrations_read_only() {
  local migrations_dir="${REPO_DIR}/scripts/migrations"
  if [[ ! -d "${migrations_dir}" ]]; then
    pass "migrations directory not found (allowed): ${migrations_dir}"
    return 0
  fi

  local sql_count
  sql_count="$(find "${migrations_dir}" -maxdepth 1 -type f -name '*.sql' | wc -l | tr -d ' ')"
  pass "migrations directory exists, sql files=${sql_count} (read-only check)"
}

wait_readyz() {
  local attempts=30
  local url="http://127.0.0.1:8000/readyz"

  for ((i=1; i<=attempts; i++)); do
    if curl -fsS --max-time 3 "${url}" >/dev/null; then
      return 0
    fi
    sleep 1
  done

  die "readyz check failed after ${attempts}s"
}

check_recent_service_errors() {
  local since_window="5 minutes ago"
  local error_lines traceback_lines

  error_lines="$(journalctl -u "${SERVICE_NAME}" --since "${since_window}" --no-pager -p err || true)"
  if [[ -n "${error_lines}" ]]; then
    log "${error_lines}"
    die "journalctl contains priority=err lines for ${SERVICE_NAME}"
  fi

  traceback_lines="$(journalctl -u "${SERVICE_NAME}" --since "${since_window}" --no-pager | grep -F "Traceback (most recent call last):" || true)"
  if [[ -n "${traceback_lines}" ]]; then
    log "${traceback_lines}"
    die "journalctl contains Traceback for ${SERVICE_NAME}"
  fi
}

check_telegram_getme() {
  local bot_name="$1"
  local token="$2"
  local response

  [[ -n "${token}" ]] || die "${bot_name}: token is empty"

  response="$(curl -sS --connect-timeout 3 --max-time 8 "https://api.telegram.org/bot${token}/getMe")" || {
    die "${bot_name}: telegram getMe request failed"
  }

  printf '%s\n' "${response}" | python3 -c '
import json
import sys

try:
    payload = json.loads(sys.stdin.read())
except json.JSONDecodeError as exc:
    print(f"invalid json: {exc}")
    sys.exit(1)

if payload.get("ok") is not True:
    print(payload)
    sys.exit(1)

result = payload.get("result") or {}
print(f"ok=true username={result.get('username')} id={result.get('id')}")
' || die "${bot_name}: telegram getMe returned non-ok"

  pass "${bot_name}: telegram getMe"
}

post_deploy_smoke_checks() {
  run_step "Smoke: /healthz" check_http_endpoint "${APP_BASE_URL}/healthz" "/healthz"
  run_step "Smoke: /readyz" check_http_endpoint "${APP_BASE_URL}/readyz" "/readyz"
  run_step "Smoke: service journal scan" check_recent_service_errors

  [[ -n "${MASTER_BOT_TOKEN:-}" ]] || die "MASTER_BOT_TOKEN is required for telegram smoke-check"
  run_step "Smoke: master bot getMe" check_telegram_getme "master bot" "${MASTER_BOT_TOKEN}"

  if [[ -n "${TEST_PERSONAL_BOT_TOKEN:-}" ]]; then
    run_step "Smoke: test personal bot getMe" check_telegram_getme "test personal bot" "${TEST_PERSONAL_BOT_TOKEN}"
  else
    log "[INFO] TEST_PERSONAL_BOT_TOKEN is not set; skipping personal bot getMe smoke-check"
  fi
}

run_checks() {
  run_step "Check command: systemctl" check_cmd systemctl
  run_step "Check command: curl" check_cmd curl
  run_step "Check command: nginx" check_cmd nginx
  run_step "Check repository" check_repo
  run_step "Check env file" check_env_file
  run_step "Check venv" check_venv
  run_step "Print git/build info" print_git_and_build_info
  run_step "Check PyYAML import" check_yaml_import
  run_step "Check systemd units" check_systemd_units
  run_step "Check /healthz" check_http_endpoint "http://127.0.0.1:8000/healthz" "/healthz"
  run_step "Check /readyz" check_http_endpoint "http://127.0.0.1:8000/readyz" "/readyz"
  run_step "Check nginx config" check_nginx
  run_step "Check migrations directory" check_migrations_read_only
  run_step "Check/apply migrations" check_migrations_applied
}

run_deploy() {
  run_step "git fetch" git -C "${REPO_DIR}" fetch origin
  run_step "git pull --ff-only origin main" git -C "${REPO_DIR}" pull --ff-only origin main

  run_step "pip install requirements" sudo -u zumbot bash -lc "cd '${REPO_DIR}' && source .venv/bin/activate && pip install -r requirements.txt"
  run_step "Install test reset command" ln -sfn "${REPO_DIR}/scripts/test_data_reset_run.py" /usr/local/bin/zumbot-test-reset

  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a

  [[ -n "${DB_URL:-}" ]] || die "DB_URL is required in ${ENV_FILE}"
  local db_url_for_cli
  db_url_for_cli="$(normalize_db_url "${DB_URL}")"
  run_step "Run SQL migrations" env DB_URL="${db_url_for_cli}" bash "${MIGRATE_SCRIPT}"

  run_step "Restart ${SERVICE_NAME}" systemctl restart "${SERVICE_NAME}"
  run_step "Wait /readyz" wait_readyz

  run_step "Post-deploy smoke-check" post_deploy_smoke_checks
  run_checks
}

usage() {
  cat <<USAGE
Usage: bash scripts/vps_deploy_check.sh [--mode checks|deploy]

Modes:
  checks (default)  - only validations, no deploy actions.
  deploy            - manual deploy + post-deploy checks.
USAGE
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --mode)
        MODE="${2:-}"
        shift 2
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        die "unknown argument: $1"
        ;;
    esac
  done

  [[ "${MODE}" == "checks" || "${MODE}" == "deploy" ]] || die "unsupported mode: ${MODE}"
}

on_exit() {
  local rc=$?
  trap - EXIT

  if [[ ${rc} -eq 0 ]]; then
    log "LOG_PATH=${LOG_PATH}"
    log "EXIT_CODE=0"
    log "RESULT=OK"
    exit 0
  fi

  log "LOG_PATH=${LOG_PATH}"
  log "EXIT_CODE=1"
  log "RESULT=FAIL"
  exit 1
}

main() {
  exec > >(tee -a "${LOG_PATH}") 2>&1
  trap on_exit EXIT

  parse_args "$@"

  log "== zumbot ${MODE} =="
  print_git_and_build_info

  if [[ "$(id -u)" -ne 0 ]]; then
    die "run as root"
  fi

  if [[ "${MODE}" == "deploy" ]]; then
    run_deploy
  else
    run_checks
  fi
}

main "$@"
