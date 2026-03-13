#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEMPLATES_DIR="$ROOT_DIR/automation/templates"
BUNDLES_ROOT="$ROOT_DIR/automation/bundles/active"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

usage() {
  cat >&2 <<'EOF'
Usage:
  automation/scripts/new_story_bundle.sh STORY_ID STORY_TITLE

Example:
  automation/scripts/new_story_bundle.sh US-AUTO-1 "Add story bundle bootstrap script"
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

  printf '%s\n' "$content"
}

render_template_to_file() {
  local template_path="$1"
  local output_path="$2"

  render_template "$template_path" > "$output_path"
}

write_context_bundle() {
  cat > "$BUNDLE_DIR/01_context_bundle.md" <<EOF
# $STORY_ID: Context Bundle

## Source of Truth
- \`docs/90_codex/CODEX_OPERATING_SYSTEM.md\`
- \`docs/90_codex/STORY_EXECUTION_CHECKLIST.md\`
- \`docs/90_codex/STORY_BUNDLE_SPEC.md\`
- <story-specific architecture/product docs>
- <relevant code entry points or adapters>

## Current Code Reality
- <What exists today that constrains implementation>
- <Nearby code/tests/docs already in scope>

## Target Architecture
- <Desired end state after this story>
- <Boundary decisions that must remain intact>

## Risks
- <Risk and mitigation>
- <Open dependency or assumption>

## Acceptance Notes
- <How the story outcome will be verified>
- <What evidence should be captured in the bundle>
EOF
}

write_file_scope() {
  cat > "$BUNDLE_DIR/02_file_scope.md" <<EOF
# $STORY_ID: File Scope

## Files Allowed To Change
- <path>
- <path>

## Files Not Allowed To Change
- <path or directory>
- <path or directory>

## Scope Notes
- <Why these files are in scope>
- <Specific boundary that must not be crossed>
EOF
}

write_review_checklist() {
  cat > "$BUNDLE_DIR/04_review_checklist.md" <<EOF
# $STORY_ID: Review Checklist

## Scope Validation
- [ ] Changes stay inside \`02_file_scope.md\`
- [ ] Non-goals remain untouched
- [ ] No unrelated refactor or formatting-only edits

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
  cat > "$BUNDLE_DIR/05_followups.md" <<EOF
# $STORY_ID: Follow-Ups

## Follow-Up Prompt Queue
- <No follow-ups yet>

## Iteration Notes
- <Review findings, accepted improvements, or deferred work>

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
  cat > "$BUNDLE_DIR/06_manual_actions.md" <<EOF
# $STORY_ID: Manual Actions

## Required Human Actions
- <Branch creation, approvals, deploy coordination, or external checks>

## Execution Notes
- <Anything Codex cannot complete automatically>

## Completion Status
- [ ] No manual actions required
- [ ] Manual actions completed and documented
EOF
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

mkdir -p "$BUNDLES_ROOT"
BUNDLE_DIR="$BUNDLES_ROOT/$STORY_ID"

[[ ! -e "$BUNDLE_DIR" ]] || fail "story bundle already exists: $BUNDLE_DIR"

cleanup() {
  if [[ -d "$BUNDLE_DIR" ]]; then
    rm -rf "$BUNDLE_DIR"
  fi
}

trap cleanup ERR

mkdir "$BUNDLE_DIR"

render_template_to_file "$TEMPLATES_DIR/story_bundle_template.md" "$BUNDLE_DIR/00_story.md"
write_context_bundle
write_file_scope
render_template_to_file "$TEMPLATES_DIR/codex_master_prompt_template.md" "$BUNDLE_DIR/03_master_prompt.md"
write_review_checklist
write_followups
write_manual_actions

trap - ERR

cat <<EOF
Created story bundle: $BUNDLE_DIR
- $BUNDLE_DIR/00_story.md
- $BUNDLE_DIR/01_context_bundle.md
- $BUNDLE_DIR/02_file_scope.md
- $BUNDLE_DIR/03_master_prompt.md
- $BUNDLE_DIR/04_review_checklist.md
- $BUNDLE_DIR/05_followups.md
- $BUNDLE_DIR/06_manual_actions.md
EOF
