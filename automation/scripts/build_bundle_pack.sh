#!/usr/bin/env bash
set -euo pipefail

# Usage:
# automation/scripts/build_bundle_pack.sh <STORY_ID>

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

if [[ $# -ne 1 ]]; then
  fail "usage: build_bundle_pack.sh <STORY_ID>"
fi

STORY_ID="$1"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ACTIVE_DIR="$ROOT_DIR/automation/bundles/active/$STORY_ID"
PACK_PATH="$ROOT_DIR/automation/bundle_packs/$STORY_ID.bundle.md"

[[ -d "$ACTIVE_DIR" ]] || fail "active bundle not found: $ACTIVE_DIR"

FILES=(
  "00_story.md"
  "01_context_bundle.md"
  "02_file_scope.md"
  "03_master_prompt.md"
  "04_review_checklist.md"
  "05_followups.md"
  "06_manual_actions.md"
)

TMP_FILE="$(mktemp)"

# Header
echo "Story-ID: $STORY_ID" > "$TMP_FILE"
echo "" >> "$TMP_FILE"

for f in "${FILES[@]}"; do
  SRC="$ACTIVE_DIR/$f"
  [[ -f "$SRC" ]] || fail "missing file: $SRC"

  echo "=== FILE: $f ===" >> "$TMP_FILE"
  cat "$SRC" >> "$TMP_FILE"
  echo "" >> "$TMP_FILE"
done

mv "$TMP_FILE" "$PACK_PATH"

echo "Bundle pack rebuilt: $PACK_PATH"