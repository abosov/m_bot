#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${AUTOMATION_ROOT_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
BUNDLE_PACKS_ROOT="${AUTOMATION_BUNDLE_PACKS_ROOT:-$ROOT_DIR/automation/bundle_packs}"
BUNDLES_ROOT="${AUTOMATION_BUNDLES_ROOT:-$ROOT_DIR/automation/bundles/active}"
VALIDATOR_SCRIPT="$SCRIPT_DIR/validate_story_bundle.sh"
REQUIRED_FILES=(
  "00_story.md"
  "01_context_bundle.md"
  "02_file_scope.md"
  "03_master_prompt.md"
  "04_review_checklist.md"
  "05_followups.md"
  "06_manual_actions.md"
)

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

usage() {
  cat >&2 <<'EOF'
Usage:
  automation/scripts/materialize_story_bundle.sh STORY_ID [PACK_PATH]

Examples:
  automation/scripts/materialize_story_bundle.sh US-AUTO-12
  automation/scripts/materialize_story_bundle.sh US-AUTO-12 automation/bundle_packs/US-AUTO-12.bundle.md
EOF
  exit 1
}

validate_story_id() {
  local story_id="$1"
  [[ "$story_id" =~ ^US-[A-Z0-9]+(-[A-Z0-9]+)*$ ]] || \
    fail "invalid STORY_ID '$story_id' (expected format like US-AUTO-12)"
}

is_required_file() {
  local candidate="$1"
  local required
  for required in "${REQUIRED_FILES[@]}"; do
    if [[ "$candidate" == "$required" ]]; then
      return 0
    fi
  done
  return 1
}

pack_story_id() {
  local pack_path="$1"
  local story_id_line
  story_id_line="$(grep -m1 '^Story-ID:[[:space:]]*' "$pack_path" || true)"
  if [[ -z "$story_id_line" ]]; then
    fail "pack is missing required metadata line: Story-ID: <STORY_ID>"
  fi
  story_id_line="${story_id_line#Story-ID:}"
  story_id_line="${story_id_line#"${story_id_line%%[![:space:]]*}"}"
  story_id_line="${story_id_line%"${story_id_line##*[![:space:]]}"}"
  printf '%s\n' "$story_id_line"
}

parse_pack_into_dir() {
  local pack_path="$1"
  local output_dir="$2"
  local line
  local current_file=""
  local output_path=""
  local seen_files=" "

  while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ "$line" =~ ^===\ FILE:\ ([A-Za-z0-9._-]+)\ ===$ ]]; then
      current_file="${BASH_REMATCH[1]}"
      if ! is_required_file "$current_file"; then
        fail "pack contains unsupported file section: $current_file"
      fi
      if [[ "$seen_files" == *" $current_file "* ]]; then
        fail "pack contains duplicate file section: $current_file"
      fi
      seen_files="${seen_files}${current_file} "
      output_path="$output_dir/$current_file"
      : > "$output_path"
      continue
    fi

    if [[ -n "$current_file" ]]; then
      printf '%s\n' "$line" >> "$output_path"
    fi
  done < "$pack_path"

  local missing=()
  local file_name
  for file_name in "${REQUIRED_FILES[@]}"; do
    if [[ "$seen_files" != *" $file_name "* ]]; then
      missing+=("$file_name")
    fi
  done

  if (( ${#missing[@]} > 0 )); then
    {
      echo "ERROR: pack is missing required file sections:"
      printf ' - %s\n' "${missing[@]}"
    } >&2
    exit 1
  fi
}

[[ $# -ge 1 && $# -le 2 ]] || usage

STORY_ID="$1"
validate_story_id "$STORY_ID"

if [[ $# -eq 2 ]]; then
  PACK_PATH="$2"
else
  PACK_PATH="$BUNDLE_PACKS_ROOT/$STORY_ID.bundle.md"
fi

[[ -f "$PACK_PATH" ]] || fail "bundle pack not found: $PACK_PATH"
[[ -x "$VALIDATOR_SCRIPT" ]] || fail "validator script not executable: $VALIDATOR_SCRIPT"

PACK_STORY_ID="$(pack_story_id "$PACK_PATH")"
[[ "$PACK_STORY_ID" == "$STORY_ID" ]] || \
  fail "pack Story-ID '$PACK_STORY_ID' does not match requested STORY_ID '$STORY_ID'"

mkdir -p "$BUNDLES_ROOT"
TMP_ROOT="$(mktemp -d "$BUNDLES_ROOT/.materialize.${STORY_ID}.XXXXXX")"
TMP_BUNDLE_DIR="$TMP_ROOT/$STORY_ID"
TARGET_BUNDLE_DIR="$BUNDLES_ROOT/$STORY_ID"
BACKUP_BUNDLE_DIR=""
mkdir -p "$TMP_BUNDLE_DIR"

cleanup() {
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

parse_pack_into_dir "$PACK_PATH" "$TMP_BUNDLE_DIR"

"$VALIDATOR_SCRIPT" "$STORY_ID" "$TMP_BUNDLE_DIR"

if [[ -e "$TARGET_BUNDLE_DIR" ]]; then
  BACKUP_BUNDLE_DIR="$BUNDLES_ROOT/.backup.${STORY_ID}.$$"
  mv "$TARGET_BUNDLE_DIR" "$BACKUP_BUNDLE_DIR"
fi

if ! mv "$TMP_BUNDLE_DIR" "$TARGET_BUNDLE_DIR"; then
  if [[ -n "$BACKUP_BUNDLE_DIR" && -d "$BACKUP_BUNDLE_DIR" ]]; then
    mv "$BACKUP_BUNDLE_DIR" "$TARGET_BUNDLE_DIR"
  fi
  fail "failed to replace active bundle directory"
fi

if [[ -n "$BACKUP_BUNDLE_DIR" && -d "$BACKUP_BUNDLE_DIR" ]]; then
  rm -rf "$BACKUP_BUNDLE_DIR"
fi

printf 'Materialized story bundle: %s\n' "$TARGET_BUNDLE_DIR"
