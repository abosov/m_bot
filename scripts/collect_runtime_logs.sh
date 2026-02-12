#!/usr/bin/env bash
set -euo pipefail

SINCE_WINDOW="${SINCE_WINDOW:-24 hours ago}"
TAIL_LINES="${TAIL_LINES:-}"
SERVICE_NAME="${SERVICE_NAME:-zumbot-backend.service}"
UTCSTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BUNDLE_DIR="/tmp/zumbot_logs_bundle_${UTCSTAMP}"
ARCHIVE_PATH="${BUNDLE_DIR}.tar.gz"

log() {
  echo "[collect-runtime-logs] $*"
}

collect_journalctl() {
  local target_file="$1"

  if ! command -v journalctl >/dev/null 2>&1; then
    log "journalctl not found; writing placeholder"
    printf '%s\n' "journalctl not available on this host" >"${target_file}"
    return 0
  fi

  if [[ -n "${TAIL_LINES}" ]]; then
    log "Collecting last ${TAIL_LINES} journalctl lines for ${SERVICE_NAME}"
    if ! journalctl -u "${SERVICE_NAME}" -n "${TAIL_LINES}" --no-pager >"${target_file}" 2>&1; then
      log "journalctl collection failed; keeping command output in ${target_file}"
    fi
  else
    log "Collecting journalctl for ${SERVICE_NAME} since: ${SINCE_WINDOW}"
    if ! journalctl -u "${SERVICE_NAME}" --since "${SINCE_WINDOW}" --no-pager >"${target_file}" 2>&1; then
      log "journalctl collection failed; keeping command output in ${target_file}"
    fi
  fi
}

copy_runtime_logs() {
  local logs_dest_dir="$1"

  if [[ -z "${LOG_DIR:-}" ]]; then
    log "LOG_DIR is not set; skipping runtime files copy"
    return 0
  fi

  if [[ ! -d "${LOG_DIR}" ]]; then
    log "LOG_DIR is set but directory does not exist (${LOG_DIR}); skipping"
    return 0
  fi

  log "Copying runtime logs from LOG_DIR=${LOG_DIR}"

  local copied_any="false"
  while IFS= read -r -d '' src_file; do
    cp -f "${src_file}" "${logs_dest_dir}/"
    copied_any="true"
  done < <(find "${LOG_DIR}" -maxdepth 1 -type f \( -name '*.log' -o -name '*.log.*' \) -print0)

  if [[ "${copied_any}" == "false" ]]; then
    log "No *.log or *.log.* files found in ${LOG_DIR}"
  fi
}

copy_deploy_logs() {
  local deploy_dest_dir="$1"
  local copied_any="false"

  shopt -s nullglob
  local deploy_files=(/tmp/zumbot_deploy_*.log /tmp/zumbot_deploy_check_*.log)
  shopt -u nullglob

  if [[ "${#deploy_files[@]}" -eq 0 ]]; then
    log "No deploy logs found in /tmp (zumbot_deploy_*.log, zumbot_deploy_check_*.log)"
    return 0
  fi

  for src_file in "${deploy_files[@]}"; do
    cp -f "${src_file}" "${deploy_dest_dir}/"
    copied_any="true"
  done

  if [[ "${copied_any}" == "true" ]]; then
    log "Copied deploy logs: ${#deploy_files[@]} file(s)"
  fi
}

main() {
  log "Preparing bundle directory: ${BUNDLE_DIR}"
  rm -rf "${BUNDLE_DIR}"
  mkdir -p "${BUNDLE_DIR}/runtime_logs" "${BUNDLE_DIR}/deploy_logs"

  collect_journalctl "${BUNDLE_DIR}/journalctl_zumbot-backend.log"
  copy_runtime_logs "${BUNDLE_DIR}/runtime_logs"
  copy_deploy_logs "${BUNDLE_DIR}/deploy_logs"

  log "Creating archive: ${ARCHIVE_PATH}"
  tar -C "/tmp" -czf "${ARCHIVE_PATH}" "$(basename "${BUNDLE_DIR}")"

  log "Done. Logs archive: ${ARCHIVE_PATH}"
}

main "$@"
