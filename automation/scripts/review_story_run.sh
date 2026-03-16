#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${AUTOMATION_ROOT_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
RUNS_ROOT="${AUTOMATION_RUNS_ROOT:-$ROOT_DIR/automation/runs}"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

working_tree_dirty() {
  local status_output
  status_output="$(git -C "$ROOT_DIR" status --porcelain --untracked-files=normal 2>/dev/null || true)"
  [[ -n "$status_output" ]]
}

print_review_safety_safe() {
  printf 'Review safety: SAFE\n'
  printf 'Reason: working tree is clean and review evidence is commit-consistent\n'
}

print_review_safety_blocked() {
  local story_id="$1"
  printf 'Review safety: BLOCKED\n'
  printf 'Reason: working tree contains uncommitted materialized changes\n'
  printf 'Next step:\n'
  printf '1. inspect changes\n'
  printf '2. commit changes\n'
  printf '3. if needed, rerun automation/scripts/run_story.sh %s\n' "$story_id"
  printf '4. rerun automation/scripts/review_gate_story_run.sh %s\n' "$story_id"
}

usage() {
  cat >&2 <<'EOF'
Usage:
  automation/scripts/review_story_run.sh STORY_ID

Example:
  automation/scripts/review_story_run.sh US-AUTO-2
EOF
  exit 1
}

validate_story_id() {
  local story_id="$1"
  [[ "$story_id" =~ ^US-[A-Z0-9]+(-[A-Z0-9]+)*$ ]] || \
    fail "invalid STORY_ID '$story_id' (expected format like US-AUTO-2)"
}

resolve_latest_run_dir() {
  local story_runs_root="$1"
  local latest_run_dir

  latest_run_dir="$(
    find "$story_runs_root" -mindepth 1 -maxdepth 1 -type d -print | LC_ALL=C sort | tail -n 1
  )"

  [[ -n "$latest_run_dir" ]] || fail "no run directories found under: $story_runs_root"
  printf '%s\n' "$latest_run_dir"
}

[[ $# -eq 1 ]] || usage

STORY_ID="$1"
validate_story_id "$STORY_ID"

STORY_RUNS_ROOT="$RUNS_ROOT/$STORY_ID"
[[ -d "$STORY_RUNS_ROOT" ]] || fail "story run root not found for '$STORY_ID': $STORY_RUNS_ROOT"

LATEST_RUN_DIR="$(resolve_latest_run_dir "$STORY_RUNS_ROOT")"

required_artifacts=(
  "manifest.md"
  "review_bundle.md"
  "chatgpt_review_prompt.md"
  "diff.patch"
  "changed_files.txt"
  "pytest.txt"
)

missing_artifacts=()
for artifact_name in "${required_artifacts[@]}"; do
  artifact_path="$LATEST_RUN_DIR/$artifact_name"
  if [[ ! -f "$artifact_path" ]]; then
    missing_artifacts+=("$artifact_path")
  fi
done

if (( ${#missing_artifacts[@]} > 0 )); then
  {
    echo "ERROR: latest run for '$STORY_ID' is missing required review artifacts:"
    printf ' - %s\n' "${missing_artifacts[@]}"
  } >&2
  exit 1
fi

printf 'Review summary\n'
printf 'STORY_ID: %s\n' "$STORY_ID"
printf 'Latest run: %s\n' "$LATEST_RUN_DIR"
printf 'Artifacts:\n'
for artifact_name in "${required_artifacts[@]}"; do
  printf ' - %s\n' "$LATEST_RUN_DIR/$artifact_name"
done

optional_artifacts=(
  "ai_review_result.md"
  "review_classification.md"
  "review_gate_result.json"
)

available_optional_artifacts=()
for artifact_name in "${optional_artifacts[@]}"; do
  artifact_path="$LATEST_RUN_DIR/$artifact_name"
  if [[ -f "$artifact_path" ]]; then
    available_optional_artifacts+=("$artifact_path")
  fi
done

if (( ${#available_optional_artifacts[@]} > 0 )); then
  printf 'Optional artifacts:\n'
  printf ' - %s\n' "${available_optional_artifacts[@]}"
fi

printf '\n'

if working_tree_dirty; then
  print_review_safety_blocked "$STORY_ID"
  fail "review blocked for '$STORY_ID': current branch has uncommitted materialized changes and is not commit-consistent"
fi

print_review_safety_safe
printf '\n'
printf 'Next step: run automation/scripts/review_gate_story_run.sh %s to generate the final gate artifact for %s.\n' "$STORY_ID" "$LATEST_RUN_DIR"
printf 'The gate resolves the latest run once and reuses that exact run directory for AI review and classification.\n'
printf 'The gate artifact is review_gate_result.json with a machine-readable decision, status, and source.\n'
