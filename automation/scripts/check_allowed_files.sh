#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

usage() {
  cat <<EOF
Usage: $(basename "$0") STORY_ID [changed-files-list] [bundle-dir]
EOF
}

[[ $# -ge 1 && $# -le 3 ]] || {
  usage >&2
  exit 1
}

STORY_ID="$1"
CHANGED_FILES_LIST="${2:-}"
BUNDLE_DIR="${3:-$ROOT_DIR/automation/bundles/active/$STORY_ID}"
SCOPE_FILE="$BUNDLE_DIR/02_file_scope.md"

[[ -d "$BUNDLE_DIR" ]] || fail "bundle directory not found: $BUNDLE_DIR"
[[ -f "$SCOPE_FILE" ]] || fail "scope file not found: $SCOPE_FILE"
if [[ -n "$CHANGED_FILES_LIST" && ! -f "$CHANGED_FILES_LIST" ]]; then
  fail "changed-files list not found: $CHANGED_FILES_LIST"
fi

ALLOWED_PATTERNS=()
while IFS= read -r pattern; do
  [[ -n "$pattern" ]] || continue
  ALLOWED_PATTERNS+=("$pattern")
done < <(
  awk '
    /^## Files Allowed To Change[[:space:]]*$/ {
      in_section=1
      next
    }
    /^## / {
      if (in_section) {
        exit
      }
    }
    in_section {
      line=$0
      gsub(/`/, "", line)
      sub(/^[[:space:]]*[-*][[:space:]]*/, "", line)
      sub(/^[[:space:]]+/, "", line)
      sub(/[[:space:]]+$/, "", line)
      if (line != "") {
        print line
      }
    }
  ' "$SCOPE_FILE"
)

[[ ${#ALLOWED_PATTERNS[@]} -gt 0 ]] || fail "no allowed file patterns found in $SCOPE_FILE"

is_allowed_file() {
  local changed_file="$1"
  local pattern prefix

  for pattern in "${ALLOWED_PATTERNS[@]}"; do
    if [[ "$pattern" == *"/**" ]]; then
      prefix="${pattern%/**}"
      if [[ -n "$prefix" && "$changed_file" == "$prefix/"* ]]; then
        return 0
      fi
      continue
    fi

    if [[ "$changed_file" == "$pattern" ]]; then
      return 0
    fi
  done

  return 1
}

VIOLATIONS=()

if [[ -n "$CHANGED_FILES_LIST" ]]; then
  while IFS= read -r changed_file; do
    [[ -n "$changed_file" ]] || continue
    if ! is_allowed_file "$changed_file"; then
      VIOLATIONS+=("$changed_file")
    fi
  done < "$CHANGED_FILES_LIST"
fi

if [[ ${#VIOLATIONS[@]} -gt 0 ]]; then
  {
    echo "ERROR: changed files outside allowed scope for story $STORY_ID:"
    printf ' - %s\n' "${VIOLATIONS[@]}"
  } >&2
  exit 1
fi
