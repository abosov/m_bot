#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: scripts/diag_fetch_local.sh <user@host> [remote_archive_path]" >&2
  exit 1
fi

VPS_HOST="$1"
REMOTE_ARCHIVE_PATH="${2:-}"
LOCAL_BASE_DIR="${HOME}/Downloads/zumbot_diag"
mkdir -p "$LOCAL_BASE_DIR"

if [[ -z "$REMOTE_ARCHIVE_PATH" ]]; then
  REMOTE_ARCHIVE_PATH="$(ssh "$VPS_HOST" "ls -1t /tmp/zumbot_diag_*.tar.gz 2>/dev/null | head -n1")"
fi

if [[ -z "$REMOTE_ARCHIVE_PATH" ]]; then
  echo "Could not resolve remote archive path." >&2
  exit 1
fi

LOCAL_ARCHIVE_PATH="${LOCAL_BASE_DIR}/$(basename "$REMOTE_ARCHIVE_PATH")"
scp "$VPS_HOST:$REMOTE_ARCHIVE_PATH" "$LOCAL_ARCHIVE_PATH"

EXTRACT_DIR="${LOCAL_BASE_DIR}/$(basename "$LOCAL_ARCHIVE_PATH" .tar.gz)"
rm -rf "$EXTRACT_DIR"
mkdir -p "$EXTRACT_DIR"
tar -xzf "$LOCAL_ARCHIVE_PATH" -C "$EXTRACT_DIR" --strip-components=1

SUMMARY_PATH="${EXTRACT_DIR}/summary.txt"
echo "Extracted package: ${EXTRACT_DIR}"
if [[ -f "$SUMMARY_PATH" ]]; then
  echo "Read summary: less ${SUMMARY_PATH}"
else
  echo "Summary file not found: ${SUMMARY_PATH}"
fi

echo "Inspect journals: ls ${EXTRACT_DIR}/journal_*.log"
if command -v lnav >/dev/null 2>&1; then
  echo "Open journals in lnav: lnav ${EXTRACT_DIR}/journal_*.log"
fi
