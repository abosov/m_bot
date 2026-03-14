#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${AUTOMATION_ROOT_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
BUNDLES_ROOT="${AUTOMATION_BUNDLES_ROOT:-$ROOT_DIR/automation/bundles/active}"
CANONICAL_PLACEHOLDER_TOKEN="_""!""_"
LEGACY_UNRESOLVED_TOKEN="<UNRESOLVED>"
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
  automation/scripts/validate_story_bundle.sh STORY_ID [BUNDLE_DIR]

Examples:
  automation/scripts/validate_story_bundle.sh US-AUTO-12
  automation/scripts/validate_story_bundle.sh US-AUTO-12 /tmp/materialized-bundle
EOF
  exit 1
}

validate_story_id() {
  local story_id="$1"
  [[ "$story_id" =~ ^US-[A-Z0-9]+(-[A-Z0-9]+)*$ ]] || \
    fail "invalid STORY_ID '$story_id' (expected format like US-AUTO-12)"
}

contains_non_whitespace() {
  local path="$1"
  grep -q '[^[:space:]]' "$path"
}

check_required_sections() {
  local file_path="$1"
  shift
  local section
  local missing=0
  for section in "$@"; do
    if ! grep -Fq "$section" "$file_path"; then
      printf ' - missing required section in %s: %s\n' "$file_path" "$section" >&2
      missing=1
    fi
  done
  return "$missing"
}

validate_required_sections() {
  local bundle_dir="$1"
  local failed=0

  check_required_sections \
    "$bundle_dir/00_story.md" \
    "## Story ID and Title" \
    "## Objective" \
    "## Scope" \
    "## Non-goals" \
    "## Dependencies" \
    "## Source of Truth" \
    "## Current Code Reality" \
    "## Target Outcome" || failed=1

  check_required_sections \
    "$bundle_dir/01_context_bundle.md" \
    "## Source of Truth" \
    "## Current Code Reality" \
    "## Architectural Intent" \
    "## Risks" \
    "## Acceptance Notes" || failed=1

  check_required_sections \
    "$bundle_dir/02_file_scope.md" \
    "## Files Allowed To Change" \
    "## Files Not Allowed To Change" || failed=1

  check_required_sections \
    "$bundle_dir/03_master_prompt.md" \
    "## Role" \
    "## Goal" \
    "## Source of Truth" \
    "## Files Allowed To Change" \
    "## Files Not Allowed To Change" \
    "## Output" || failed=1

  check_required_sections \
    "$bundle_dir/04_review_checklist.md" \
    "## Scope Validation" \
    "## Functional Validation" \
    "## Verification" || failed=1

  check_required_sections \
    "$bundle_dir/05_followups.md" \
    "## Follow-Up Prompt Queue" \
    "## Iteration Notes" || failed=1

  check_required_sections \
    "$bundle_dir/06_manual_actions.md" \
    "## Required Human Actions" \
    "## Completion Status" || failed=1

  return "$failed"
}

[[ $# -ge 1 && $# -le 2 ]] || usage

STORY_ID="$1"
validate_story_id "$STORY_ID"

if [[ $# -eq 2 ]]; then
  BUNDLE_DIR="$2"
else
  BUNDLE_DIR="$BUNDLES_ROOT/$STORY_ID"
fi

[[ -d "$BUNDLE_DIR" ]] || fail "story bundle directory not found: $BUNDLE_DIR"

missing_files=()
empty_files=()
placeholder_files=()
legacy_unresolved_files=()

for file_name in "${REQUIRED_FILES[@]}"; do
  file_path="$BUNDLE_DIR/$file_name"
  if [[ ! -f "$file_path" ]]; then
    missing_files+=("$file_path")
    continue
  fi
  if ! contains_non_whitespace "$file_path"; then
    empty_files+=("$file_path")
  fi
  if grep -Fq "$CANONICAL_PLACEHOLDER_TOKEN" "$file_path"; then
    placeholder_files+=("$file_path")
  fi
  if grep -Fq "$LEGACY_UNRESOLVED_TOKEN" "$file_path"; then
    legacy_unresolved_files+=("$file_path")
  fi
done

has_errors=0
if (( ${#missing_files[@]} > 0 )); then
  echo "ERROR: bundle is missing required files:" >&2
  printf ' - %s\n' "${missing_files[@]}" >&2
  has_errors=1
fi

if (( ${#empty_files[@]} > 0 )); then
  echo "ERROR: bundle has empty files:" >&2
  printf ' - %s\n' "${empty_files[@]}" >&2
  has_errors=1
fi

if (( ${#placeholder_files[@]} > 0 )); then
  echo "ERROR: bundle still contains unresolved canonical placeholder tokens:" >&2
  printf ' - %s\n' "${placeholder_files[@]}" >&2
  has_errors=1
fi

if (( ${#legacy_unresolved_files[@]} > 0 )); then
  echo "ERROR: bundle still contains unresolved <UNRESOLVED> placeholders:" >&2
  printf ' - %s\n' "${legacy_unresolved_files[@]}" >&2
  has_errors=1
fi

if ! validate_required_sections "$BUNDLE_DIR"; then
  has_errors=1
fi

if (( has_errors == 1 )); then
  exit 1
fi

printf 'Bundle validation passed: %s\n' "$BUNDLE_DIR"
