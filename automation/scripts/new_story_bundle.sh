#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${AUTOMATION_ROOT_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
TEMPLATES_DIR="${AUTOMATION_TEMPLATES_DIR:-$ROOT_DIR/automation/templates}"
BUNDLE_PACKS_ROOT="${AUTOMATION_BUNDLE_PACKS_ROOT:-$ROOT_DIR/automation/bundle_packs}"
CANONICAL_PLACEHOLDER_TOKEN="_""!""_"
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
  automation/scripts/new_story_bundle.sh STORY_ID STORY_TITLE

Example:
  automation/scripts/new_story_bundle.sh US-AUTO-1 "Bundle pack bootstrap"
EOF
  exit 1
}

require_file() {
  local path="$1"
  [[ -f "$path" ]] || fail "required template not found: $path"
}

validate_story_id() {
  local story_id="$1"
  [[ "$story_id" =~ ^US-[A-Z0-9]+(-[A-Z0-9]+)*$ ]] || \
    fail "invalid STORY_ID '$story_id' (expected format like US-AUTO-1)"
}

trim() {
  local value="$1"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s' "$value"
}

render_template() {
  local template_path="$1"
  local content

  content="$(<"$template_path")"
  content="${content//<STORY-ID>/$STORY_ID}"
  content="${content//<Story Title>/$STORY_TITLE}"
  content="${content//<PR Title>/$STORY_TITLE}"
  content="${content//<Short Goal>/$STORY_TITLE}"
  content="${content//<N>/1}"
  content="${content//<UNRESOLVED>/$CANONICAL_PLACEHOLDER_TOKEN}"

  printf '%s\n' "$content"
}

render_template_to_file() {
  local template_path="$1"
  local output_path="$2"
  render_template "$template_path" > "$output_path"
}

write_context_bundle() {
  cat > "$1" <<EOF
# $STORY_ID: Context Bundle

## Source of Truth
- \`docs/90_codex/CODEX_OPERATING_SYSTEM.md\`
- \`docs/90_codex/STORY_EXECUTION_CHECKLIST.md\`
- \`docs/90_codex/STORY_BUNDLE_SPEC.md\`
- $CANONICAL_PLACEHOLDER_TOKEN

## Current Code Reality
- $CANONICAL_PLACEHOLDER_TOKEN

## Architectural Intent
- $CANONICAL_PLACEHOLDER_TOKEN

## Risks
- $CANONICAL_PLACEHOLDER_TOKEN

## Acceptance Notes
- $CANONICAL_PLACEHOLDER_TOKEN
EOF
}

write_file_scope() {
  cat > "$1" <<EOF
# $STORY_ID: File Scope

## Files Allowed To Change
- $CANONICAL_PLACEHOLDER_TOKEN

## Files Not Allowed To Change
- $CANONICAL_PLACEHOLDER_TOKEN

## Scope Notes
- $CANONICAL_PLACEHOLDER_TOKEN
EOF
}

write_review_checklist() {
  cat > "$1" <<EOF
# $STORY_ID: Review Checklist

## Scope Validation
- [ ] Changes stay inside \`02_file_scope.md\`
- [ ] Source-of-truth files are complete and resolved
- [ ] No unrelated refactor or formatting-only edits

## Functional Validation
- [ ] Bundle materializes into all seven required files
- [ ] Validation blocks unresolved placeholders and incomplete structure
- [ ] \`run_story.sh\` blocks invalid bundles

## Architecture / Source of Truth
- [ ] Source-of-truth docs are listed and followed
- [ ] Architecture boundaries remain intact
- [ ] Docs/process updates are included when required

## Verification
- [ ] Targeted tests/validation commands are recorded
- [ ] Manual verification steps are recorded when needed
- [ ] Risks and follow-ups are captured before merge

## Review Prompt Seed

\`\`\`md
$(render_template "$TEMPLATES_DIR/review_prompt_template.md")
\`\`\`
EOF
}

write_followups() {
  cat > "$1" <<EOF
# $STORY_ID: Follow-Ups

## Follow-Up Prompt Queue
- $CANONICAL_PLACEHOLDER_TOKEN

## Iteration Notes
- $CANONICAL_PLACEHOLDER_TOKEN

## Follow-Up Prompt Template

\`\`\`md
$(render_template "$TEMPLATES_DIR/followup_prompt_template.md")
\`\`\`

## PR Description Template

\`\`\`md
$(render_template "$TEMPLATES_DIR/pr_description_template.md")
\`\`\`
EOF
}

write_manual_actions() {
  cat > "$1" <<EOF
# $STORY_ID: Manual Actions

## Required Human Actions
- $CANONICAL_PLACEHOLDER_TOKEN

## Execution Notes
- $CANONICAL_PLACEHOLDER_TOKEN

## Completion Status
- [ ] No manual actions required
- [ ] Manual actions completed and documented
EOF
}

write_bundle_pack() {
  local temp_dir="$1"
  local pack_path="$2"

  cat > "$pack_path" <<EOF
# Story Bundle Pack
Story-ID: $STORY_ID
Version: 1

This pack is the single source of truth for materialized story bundle files.

EOF

  for file_name in "${REQUIRED_FILES[@]}"; do
    {
      printf '=== FILE: %s ===\n' "$file_name"
      cat "$temp_dir/$file_name"
      printf '\n'
    } >> "$pack_path"
  done
}

[[ $# -ge 2 ]] || usage

STORY_ID="$1"
shift
STORY_TITLE="$(trim "$*")"

[[ -n "$STORY_TITLE" ]] || fail "STORY_TITLE must not be empty"
validate_story_id "$STORY_ID"

require_file "$TEMPLATES_DIR/story_bundle_template.md"
require_file "$TEMPLATES_DIR/codex_master_prompt_template.md"
require_file "$TEMPLATES_DIR/followup_prompt_template.md"
require_file "$TEMPLATES_DIR/review_prompt_template.md"
require_file "$TEMPLATES_DIR/pr_description_template.md"

mkdir -p "$BUNDLE_PACKS_ROOT"
PACK_FILE="$BUNDLE_PACKS_ROOT/$STORY_ID.bundle.md"

[[ ! -e "$PACK_FILE" ]] || fail "bundle pack already exists: $PACK_FILE"

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/story-pack.${STORY_ID}.XXXXXX")"

cleanup() {
  if [[ -d "$TMP_DIR" ]]; then
    rm -rf "$TMP_DIR"
  fi
  if [[ -f "$PACK_FILE" ]]; then
    rm -f "$PACK_FILE"
  fi
}

trap cleanup ERR

render_template_to_file "$TEMPLATES_DIR/story_bundle_template.md" "$TMP_DIR/00_story.md"
write_context_bundle "$TMP_DIR/01_context_bundle.md"
write_file_scope "$TMP_DIR/02_file_scope.md"
render_template_to_file "$TEMPLATES_DIR/codex_master_prompt_template.md" "$TMP_DIR/03_master_prompt.md"
write_review_checklist "$TMP_DIR/04_review_checklist.md"
write_followups "$TMP_DIR/05_followups.md"
write_manual_actions "$TMP_DIR/06_manual_actions.md"
write_bundle_pack "$TMP_DIR" "$PACK_FILE"

rm -rf "$TMP_DIR"

trap - ERR

cat <<EOF
Created bundle pack: $PACK_FILE
Next steps:
- Fill unresolved sections marked with the canonical placeholder token.
- Materialize bundle files: automation/scripts/materialize_story_bundle.sh $STORY_ID
- Validate bundle files: automation/scripts/validate_story_bundle.sh $STORY_ID
EOF
