#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${AUTOMATION_ROOT_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
RUNS_ROOT="${AUTOMATION_RUNS_ROOT:-$ROOT_DIR/automation/runs}"
RUN_DIR_OVERRIDE="${AUTOMATION_RUN_DIR:-}"
EPHEMERAL_LEDGER_PATH="automation/story_change_ledger.jsonl"
EPHEMERAL_LEDGER_EXCLUDE_PATHSPEC=":(exclude)$EPHEMERAL_LEDGER_PATH"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

working_tree_dirty() {
  local status_output
  status_output="$(git -C "$ROOT_DIR" status --porcelain --untracked-files=normal -- . "$EPHEMERAL_LEDGER_EXCLUDE_PATHSPEC" 2>/dev/null || true)"
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
  printf 'Reason: workspace-only changes would make review diverge from committed HEAD and origin/main...HEAD\n'
  printf 'Next step:\n'
  printf '1. inspect the workspace-only changes\n'
  printf '2. commit the changes if they belong in the reviewed diff, or discard them if they do not\n'
  printf '3. if you committed review-relevant changes, rerun automation/scripts/run_story.sh %s\n' "$story_id"
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

run_manifest_companion_filter_enabled() {
  local run_dir="$1"
  local manifest_file="$run_dir/manifest.md"
  local companion_filter_mode

  [[ -f "$manifest_file" ]] || return 1
  companion_filter_mode="$(manifest_value "$manifest_file" "execution_companion_filter_mode")"
  [[ "$companion_filter_mode" == "enabled" ]]
}

resolve_review_artifact_base() {
  local manifest_file="$1"
  local review_artifact_base

  review_artifact_base="$(manifest_value "$manifest_file" "review_artifact_base")"
  if [[ -z "$review_artifact_base" ]]; then
    return 1
  fi

  git -C "$ROOT_DIR" rev-parse --verify "${review_artifact_base}^{commit}" 2>/dev/null || return 1
}

manifest_source_of_truth_head() {
  local manifest_file="$1"
  local starting_head isolated_worktree_head

  isolated_worktree_head="$(manifest_value "$manifest_file" "isolated_worktree_head")"
  if [[ "$isolated_worktree_head" =~ ^[0-9a-f]{40}$ ]]; then
    printf '%s\n' "$isolated_worktree_head"
    return 0
  fi

  starting_head="$(manifest_value "$manifest_file" "starting_head")"
  if [[ -n "$starting_head" ]]; then
    printf '%s\n' "$starting_head"
    return 0
  fi

  if [[ -n "$isolated_worktree_head" ]]; then
    printf '%s\n' "$isolated_worktree_head"
  fi
}

is_story_artifact_review_ignored_path() {
  local story_id="$1"
  local path="$2"

  [[ "$path" == "automation/bundle_packs/$story_id.bundle.md" ]] && return 0
  [[ "$path" == "automation/bundles/active/$story_id" ]] && return 0
  [[ "$path" == automation/bundles/active/$story_id/* ]] && return 0

  return 1
}

is_non_runtime_companion_artifact_path() {
  local path="${1#./}"

  case "$path" in
    docs/90_codex/epics/US-AUTO_REGISTRY.md)
      # Exclude only known non-runtime companion artifacts. Everything else,
      # including automation scripts, tests, and execution-governing docs,
      # stays in the runtime/review surface.
      return 0
      ;;
  esac

  return 1
}

is_review_fidelity_ignored_path() {
  local story_id="$1"
  local run_dir="$2"
  local path="$3"

  if is_story_artifact_review_ignored_path "$story_id" "$path"; then
    return 0
  fi

  run_manifest_companion_filter_enabled "$run_dir" || return 1
  is_non_runtime_companion_artifact_path "$path"
}

filter_review_fidelity_paths() {
  local story_id="$1"
  local run_dir="$2"
  local output_file="$3"
  local tmp

  tmp="$(mktemp)"

  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    if is_review_fidelity_ignored_path "$story_id" "$run_dir" "$path"; then
      continue
    fi
    printf '%s\n' "$path"
  done | LC_ALL=C sort -u > "$tmp"

  mv "$tmp" "$output_file"
}

filter_review_fidelity_diff() {
  local story_id="$1"
  local run_dir="$2"
  local line file
  local skip=0

  while IFS= read -r line; do
    if [[ "$line" =~ ^diff\ --git\ a/(.+)\ b/(.+)$ ]]; then
      file="${BASH_REMATCH[1]}"
      if is_review_fidelity_ignored_path "$story_id" "$run_dir" "$file"; then
        skip=1
        continue
      fi
      skip=0
    fi

    if [[ "$skip" == "1" ]]; then
      continue
    fi

    printf '%s\n' "$line"
  done
}

sorted_changed_files_to() {
  local story_id="$1"
  local run_dir="$2"
  local changed_files_file="$3"
  local output_file="$4"
  local tmp

  tmp="$(mktemp)"

  sed '/^$/d' "$changed_files_file" \
    | filter_review_fidelity_paths "$story_id" "$run_dir" "$tmp"

  mv "$tmp" "$output_file"
}

recompute_filtered_changed_files_for_run_to() {
  local story_id="$1"
  local run_dir="$2"
  local output_file="$3"
  local manifest_file="$run_dir/manifest.md"
  local review_artifact_base run_head tmp

  [[ -f "$manifest_file" ]] || return 1

  review_artifact_base="$(resolve_review_artifact_base "$manifest_file" || true)"
  run_head="$(manifest_source_of_truth_head "$manifest_file")"

  [[ "$review_artifact_base" =~ ^[0-9a-f]{40}$ ]] || return 1
  [[ "$run_head" =~ ^[0-9a-f]{40}$ ]] || return 1

  tmp="$(mktemp)"

  git -C "$ROOT_DIR" diff --name-only "$review_artifact_base" "$run_head" -- . "$EPHEMERAL_LEDGER_EXCLUDE_PATHSPEC" \
    | sed '/^$/d' \
    | while IFS= read -r path; do
        [[ -n "$path" ]] || continue
        if is_review_fidelity_ignored_path "$story_id" "$run_dir" "$path"; then
          continue
        fi
        printf '%s\n' "$path"
      done \
    | LC_ALL=C sort -u > "$tmp"

  mv "$tmp" "$output_file"
}

recompute_filtered_diff_patch_for_run_to() {
  local story_id="$1"
  local run_dir="$2"
  local output_file="$3"
  local manifest_file="$run_dir/manifest.md"
  local review_artifact_base run_head

  [[ -f "$manifest_file" ]] || return 1

  review_artifact_base="$(resolve_review_artifact_base "$manifest_file" || true)"
  run_head="$(manifest_source_of_truth_head "$manifest_file")"

  [[ "$review_artifact_base" =~ ^[0-9a-f]{40}$ ]] || return 1
  [[ "$run_head" =~ ^[0-9a-f]{40}$ ]] || return 1

  git -C "$ROOT_DIR" diff "$review_artifact_base" "$run_head" -- . "$EPHEMERAL_LEDGER_EXCLUDE_PATHSPEC" \
    | filter_review_fidelity_diff "$story_id" "$run_dir" > "$output_file"
}

run_filtered_review_artifacts_match_recomputed_surface() {
  local story_id="$1"
  local run_dir="$2"
  local changed_files_artifact="$run_dir/changed_files.txt"
  local diff_artifact="$run_dir/diff.patch"
  local expected_changed_files normalized_changed_files expected_diff normalized_diff

  [[ -f "$changed_files_artifact" ]] || return 1
  [[ -f "$diff_artifact" ]] || return 1

  expected_changed_files="$(mktemp)"
  normalized_changed_files="$(mktemp)"
  expected_diff="$(mktemp)"
  normalized_diff="$(mktemp)"

  if ! recompute_filtered_changed_files_for_run_to "$story_id" "$run_dir" "$expected_changed_files"; then
    rm -f "$expected_changed_files" "$normalized_changed_files" "$expected_diff" "$normalized_diff"
    return 1
  fi
  sorted_changed_files_to "$story_id" "$run_dir" "$changed_files_artifact" "$normalized_changed_files"

  if ! recompute_filtered_diff_patch_for_run_to "$story_id" "$run_dir" "$expected_diff"; then
    rm -f "$expected_changed_files" "$normalized_changed_files" "$expected_diff" "$normalized_diff"
    return 1
  fi
  filter_review_fidelity_diff "$story_id" "$run_dir" < "$diff_artifact" > "$normalized_diff"

  if ! cmp -s "$expected_changed_files" "$normalized_changed_files"; then
    rm -f "$expected_changed_files" "$normalized_changed_files" "$expected_diff" "$normalized_diff"
    return 1
  fi

  if ! cmp -s "$expected_diff" "$normalized_diff"; then
    rm -f "$expected_changed_files" "$normalized_changed_files" "$expected_diff" "$normalized_diff"
    return 1
  fi

  rm -f "$expected_changed_files" "$normalized_changed_files" "$expected_diff" "$normalized_diff"
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

if working_tree_dirty; then
  print_review_safety_blocked "$STORY_ID" "$LATEST_RUN_DIR"
  fail "review blocked for '$STORY_ID': workspace-only changes would make review diverge from committed HEAD and origin/main...HEAD"
fi

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

if run_manifest_companion_filter_enabled "$LATEST_RUN_DIR"; then
  run_filtered_review_artifacts_match_recomputed_surface "$STORY_ID" "$LATEST_RUN_DIR" || \
    fail "review blocked for '$STORY_ID': filtered review artifacts are stale or inconsistent with recomputed baseline"
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

print_review_safety_safe
printf '\n'

printf 'Workflow helper (source of truth): %s\n' "$(resume_next_command "analyze_story_run.sh" "$STORY_ID" "$LATEST_RUN_DIR")"
printf 'Deterministic gate command: %s\n' "$(resume_next_command "review_gate_story_run.sh" "$STORY_ID" "$LATEST_RUN_DIR")"
printf 'Use analyze_story_run.sh to determine current stage, resume safety, and next recommended command.\n'
printf 'This script only provides a summary of artifacts and safety state and does not enforce workflow transitions.\n'
