#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-https://zumbot.ru}"
SLUG_PATH="${SLUG_PATH:-/TsarevaE_12}"

check_status() {
  local path="$1"
  local expected="$2"
  local code
  code="$(curl -sS -o /tmp/site_routes_smoke_body -w '%{http_code}' "${BASE_URL}${path}")"

  if [[ "${code}" != "${expected}" ]]; then
    echo "[FAIL] ${path}: expected ${expected}, got ${code}"
    return 1
  fi

  echo "[PASS] ${path}: HTTP ${code}"
}

check_slug_html() {
  local path="$1"
  local headers
  headers="$(curl -sS -D - -o /tmp/site_routes_smoke_body "${BASE_URL}${path}")"
  local code
  code="$(printf '%s' "${headers}" | awk 'NR==1 {print $2}')"

  if [[ "${code}" != "200" ]]; then
    echo "[FAIL] ${path}: expected 200, got ${code}"
    return 1
  fi

  if ! printf '%s' "${headers}" | tr -d '\r' | grep -qi '^Content-Type: text/html'; then
    echo "[FAIL] ${path}: expected Content-Type text/html"
    return 1
  fi

  echo "[PASS] ${path}: HTTP 200 + Content-Type text/html"
}

check_status "/pricing" "200"
check_status "/api/healthz" "200"
check_slug_html "${SLUG_PATH}"

echo "[OK] site routes smoke passed"
