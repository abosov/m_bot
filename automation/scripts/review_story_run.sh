#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${AUTOMATION_ROOT_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
RUNS_ROOT="${AUTOMATION_RUNS_ROOT:-$ROOT_DIR/automation/runs}"
RUN_DIR_OVERRIDE="${AUTOMATION_RUN_DIR:-}"

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
  local run_dir="$2"
  printf 'Review safety: BLOCKED\n'
  printf 'Reason: working tree contains uncommitted materialized changes\n'
  printf 'Next step:\n'
  printf '1. inspect changes\n'
  printf '2. commit changes\n'
  printf '3. if needed, rerun automation/scripts/run_story.sh %s\n' "$story_id"
  printf '4. run %s\n' "$(resume_next_command "analyze_story_run.sh" "$story_id" "$run_dir")"
  printf '5. follow the next recommended command from analyze output\n'
}

usage() {
  cat >&2 <<'EOF'
Usage:
  automation/scripts/review_story_run.sh STORY_ID

Example:
  automation/scripts/review_story_run.sh US-AUTO-2
  AUTOMATION_RUN_DIR=automation/runs/US-AUTO-2/2026-03-13_11-00-00 automation/scripts/review_story_run.sh US-AUTO-2
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

normalize_path() {
  local path="$1"

  if [[ "$path" = /* ]]; then
    printf '%s\n' "$path"
  else
    printf '%s\n' "$ROOT_DIR/$path"
  fi
}

canonicalize_path() {
  local path="$1"
  python3 -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' "$path"
}

manifest_value() {
  local manifest_file="$1"
  local key="$2"
  [[ -f "$manifest_file" ]] || return 0

  sed -n -E "s/^-[[:space:]]+${key}:[[:space:]]*(.*)$/\\1/p" "$manifest_file" | head -n 1
}

resolve_target_run_dir() {
  local story_runs_root="$1"
  local run_dir_override="$2"
  local normalized_override canonical_override canonical_story_runs_root manifest_story_id

  if [[ -n "$run_dir_override" ]]; then
    normalized_override="$(normalize_path "$run_dir_override")"
    [[ -d "$normalized_override" ]] || fail "AUTOMATION_RUN_DIR does not exist: $normalized_override"

    canonical_override="$(canonicalize_path "$normalized_override")"
    canonical_story_runs_root="$(canonicalize_path "$story_runs_root")"

    case "$canonical_override" in
      "$canonical_story_runs_root"/*) ;;
      *) fail "AUTOMATION_RUN_DIR must be inside story run root: $story_runs_root" ;;
    esac

    manifest_story_id="$(manifest_value "$canonical_override/manifest.md" "story_id" || true)"
    if [[ -n "$manifest_story_id" && "$manifest_story_id" != "$STORY_ID" ]]; then
      fail "AUTOMATION_RUN_DIR manifest story_id '$manifest_story_id' does not match requested story '$STORY_ID'"
    fi

    printf '%s\n' "$canonical_override"
    return 0
  fi

  resolve_latest_run_dir "$story_runs_root"
}

resume_next_command() {
  local script_name="$1"
  local story_id="$2"
  local run_dir="$3"

  printf 'AUTOMATION_RUN_DIR=%q automation/scripts/%s %q\n' "$run_dir" "$script_name" "$story_id"
}

[[ $# -eq 1 ]] || usage

STORY_ID="$1"
validate_story_id "$STORY_ID"

STORY_RUNS_ROOT="$RUNS_ROOT/$STORY_ID"
[[ -d "$STORY_RUNS_ROOT" ]] || fail "story run root not found for '$STORY_ID': $STORY_RUNS_ROOT"

LATEST_RUN_DIR="$(resolve_target_run_dir "$STORY_RUNS_ROOT" "$RUN_DIR_OVERRIDE")"

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
  print_review_safety_blocked "$STORY_ID" "$LATEST_RUN_DIR"
  fail "review blocked for '$STORY_ID': current branch has uncommitted materialized changes and is not commit-consistent"
fi

print_review_safety_safe
printf '\n'

printf 'Workflow helper (source of truth): %s\n' "$(resume_next_command "analyze_story_run.sh" "$STORY_ID" "$LATEST_RUN_DIR")"
printf 'Use analyze_story_run.sh to determine current stage, resume safety, and next recommended command.\n'
printf 'This script only provides a summary of artifacts and safety state and does not enforce workflow transitions.\n'