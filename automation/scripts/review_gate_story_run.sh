#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${AUTOMATION_ROOT_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
RUNS_ROOT="${AUTOMATION_RUNS_ROOT:-$ROOT_DIR/automation/runs}"
RUN_DIR_OVERRIDE="${AUTOMATION_RUN_DIR:-}"

# shellcheck source=automation/scripts/merge_recommendation_contract.sh
source "$SCRIPT_DIR/merge_recommendation_contract.sh"
# shellcheck source=automation/scripts/story_change_ledger.sh
source "$SCRIPT_DIR/story_change_ledger.sh"

AI_REVIEW_SCRIPT="$SCRIPT_DIR/ai_review_story_run.sh"
CLASSIFY_REVIEW_SCRIPT="$SCRIPT_DIR/classify_review_story_run.sh"

AI_REVIEW_FILE_NAME="ai_review_result.md"
CLASSIFICATION_FILE_NAME="review_classification.md"
GATE_RESULT_FILE_NAME="review_gate_result.json"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

working_tree_dirty() {
  local status_output
  status_output="$(git -C "$ROOT_DIR" status --porcelain --untracked-files=normal 2>/dev/null || true)"
  [[ -n "$status_output" ]]
}

fail_review_gate_dirty_working_tree() {
  local story_id="$1"
  local run_dir="${2:-}"
  {
    printf "ERROR: review gate blocked for '%s'\n" "$story_id"
    printf 'Reason: current branch has uncommitted changes; review artifacts would not match committed state\n'
    printf 'Required action:\n'
    printf ' - inspect and commit the materialized changes\n'
    printf ' - if needed, rerun automation/scripts/run_story.sh %s\n' "$story_id"
    if [[ -n "$run_dir" ]]; then
      printf ' - inspect the pinned run with AUTOMATION_RUN_DIR=%q automation/scripts/analyze_story_run.sh %q\n' "$run_dir" "$story_id"
      printf ' - rerun AUTOMATION_RUN_DIR=%q automation/scripts/review_gate_story_run.sh %q\n' "$run_dir" "$story_id"
    else
      printf ' - inspect the latest run with automation/scripts/analyze_story_run.sh %s\n' "$story_id"
      printf ' - rerun automation/scripts/review_gate_story_run.sh %s\n' "$story_id"
    fi
  } >&2
  exit 1
}

usage() {
  cat >&2 <<'EOF'
Usage:
  automation/scripts/review_gate_story_run.sh STORY_ID

Example:
  automation/scripts/review_gate_story_run.sh US-AUTO-16
  AUTOMATION_RUN_DIR=automation/runs/US-AUTO-16/2026-03-14_18-56-10 automation/scripts/review_gate_story_run.sh US-AUTO-16
EOF
  exit 1
}

require_file() {
  local path="$1"
  [[ -f "$path" ]] || fail "required file not found: $path"
}

validate_story_id() {
  local story_id="$1"
  [[ "$story_id" =~ ^US-[A-Z0-9]+(-[A-Z0-9]+)*$ ]] || \
    fail "invalid STORY_ID '$story_id' (expected format like US-AUTO-16)"
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

extract_merge_recommendation() {
  local classification_file="$1"

  extract_strict_merge_recommendation "$classification_file"
}

json_escape() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

current_checkout_head() {
  if ! git -C "$ROOT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    return 0
  fi

  git -C "$ROOT_DIR" rev-parse --verify HEAD 2>/dev/null || true
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

head_matches_expected() {
  local expected_head="$1"
  local current_head="$2"

  if [[ "$expected_head" == "$current_head" ]]; then
    return 0
  fi

  if [[ "$expected_head" =~ ^[0-9a-f]{7,39}$ ]] && [[ "$current_head" == "$expected_head"* ]]; then
    return 0
  fi

  return 1
}

head_consistency_status() {
  local manifest_file="$1"
  local expected_head current_head

  expected_head="$(manifest_source_of_truth_head "$manifest_file")"
  if [[ -z "$expected_head" ]]; then
    printf 'unknown:manifest_head_missing\n'
    return 0
  fi

  current_head="$(current_checkout_head)"
  if [[ -z "$current_head" ]]; then
    printf 'unknown:current_head_unavailable:%s\n' "$expected_head"
    return 0
  fi

  if head_matches_expected "$expected_head" "$current_head"; then
    printf 'match:%s\n' "$current_head"
    return 0
  fi

  printf 'mismatch:%s:%s\n' "$expected_head" "$current_head"
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

review_artifact_fidelity_status() {
  local run_dir="$1"
  local manifest_file="$2"
  local diff_artifact changed_files_artifact
  local review_artifact_base
  local expected_diff_file expected_changed_files_file artifact_changed_files_file

  diff_artifact="$run_dir/diff.patch"
  changed_files_artifact="$run_dir/changed_files.txt"

  if [[ ! -f "$diff_artifact" ]]; then
    printf 'reject\treview_diff_artifact_missing\trequired file not found: %s\n' "$diff_artifact"
    return 0
  fi

  if [[ ! -f "$changed_files_artifact" ]]; then
    printf 'reject\treview_changed_files_artifact_missing\trequired file not found: %s\n' "$changed_files_artifact"
    return 0
  fi

  if ! review_artifact_base="$(resolve_review_artifact_base "$manifest_file")"; then
    printf 'reject\treview_artifact_base_missing\trun manifest is missing or has invalid review_artifact_base; rerun automation/scripts/run_story.sh %s\n' "$STORY_ID"
    return 0
  fi

  expected_diff_file="$(mktemp)"
  expected_changed_files_file="$(mktemp)"
  artifact_changed_files_file="$(mktemp)"

  if ! git -C "$ROOT_DIR" diff "$review_artifact_base" -- > "$expected_diff_file"; then
    rm -f "$expected_diff_file" "$expected_changed_files_file" "$artifact_changed_files_file"
    printf 'reject\treview_diff_generation_failed\tunable to regenerate authoritative diff from review_artifact_base %s\n' "$review_artifact_base"
    return 0
  fi

  if ! git -C "$ROOT_DIR" diff --name-only "$review_artifact_base" -- | sed '/^$/d' | LC_ALL=C sort -u > "$expected_changed_files_file"; then
    rm -f "$expected_diff_file" "$expected_changed_files_file" "$artifact_changed_files_file"
    printf 'reject\treview_changed_files_generation_failed\tunable to regenerate authoritative changed_files from review_artifact_base %s\n' "$review_artifact_base"
    return 0
  fi

  sed '/^$/d' "$changed_files_artifact" | LC_ALL=C sort -u > "$artifact_changed_files_file"

  if ! cmp -s "$artifact_changed_files_file" "$expected_changed_files_file"; then
    rm -f "$expected_diff_file" "$expected_changed_files_file" "$artifact_changed_files_file"
    printf 'reject\treview_changed_files_mismatch\treview artifact changed_files.txt is stale or inconsistent with current HEAD diff; rerun automation/scripts/run_story.sh %s\n' "$STORY_ID"
    return 0
  fi

  if ! cmp -s "$diff_artifact" "$expected_diff_file"; then
    rm -f "$expected_diff_file" "$expected_changed_files_file" "$artifact_changed_files_file"
    printf 'reject\treview_diff_patch_mismatch\treview artifact diff.patch is stale or inconsistent with current HEAD diff; rerun automation/scripts/run_story.sh %s\n' "$STORY_ID"
    return 0
  fi

  rm -f "$expected_diff_file" "$expected_changed_files_file" "$artifact_changed_files_file"
  printf 'ok\treview_artifact_fidelity_valid\tartifact fidelity verified against review_artifact_base %s\n' "$review_artifact_base"
}

write_gate_result() {
  local gate_result_file="$1"
  local story_id="$2"
  local run_id="$3"
  local run_dir="$4"
  local ai_review_file="$5"
  local classification_file="$6"
  local reviewed_head="$7"
  local checkout_head="$8"
  local decision="$9"
  local decision_source="${10}"
  local status="${11}"
  local reason="${12}"
  local tmp_file

  tmp_file="$(mktemp "${gate_result_file}.tmp.XXXXXX")"

  cat >"$tmp_file" <<EOF
{
  "story_id": "$(json_escape "$story_id")",
  "run_id": "$(json_escape "$run_id")",
  "run_dir": "$(json_escape "$run_dir")",
  "ai_review_result": "$(json_escape "$ai_review_file")",
  "review_classification_result": "$(json_escape "$classification_file")",
  "reviewed_head": "$(json_escape "$reviewed_head")",
  "checkout_head": "$(json_escape "$checkout_head")",
  "decision": "$(json_escape "$decision")",
  "status": "$(json_escape "$status")",
  "decision_source": "$(json_escape "$decision_source")",
  "reason": "$(json_escape "$reason")"
}
EOF
  mv "$tmp_file" "$gate_result_file"
}


append_manifest_artifact() {
  local manifest_file="$1"
  local artifact_name="$2"

  grep -Fqx -- "- $artifact_name" "$manifest_file" && return 0
  printf '%s\n' "- $artifact_name" >>"$manifest_file"
}

update_manifest_gate_artifacts() {
  local manifest_file="$1"
  local run_dir="$2"

  [[ -f "$manifest_file" ]] || return 0
  grep -Fq "## Artifacts" "$manifest_file" || return 0

  local artifact_name
  for artifact_name in \
    "ai_review_result.md" \
    "review_classification.md" \
    "review_gate_result.json"
  do
    [[ -f "$run_dir/$artifact_name" ]] || continue
    append_manifest_artifact "$manifest_file" "$artifact_name"
  done
}

append_review_ledger_events() {
  local decision="$1"
  local decision_source="$2"
  local status="$3"
  local reason="$4"
  local branch_name
  local artifact_path

  branch_name="$(git -C "$ROOT_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
  if [[ "$branch_name" == "HEAD" ]]; then
    branch_name=""
  fi
  artifact_path="automation/runs/$STORY_ID/$RUN_ID/$GATE_RESULT_FILE_NAME"

  append_story_change_ledger_entry \
    "$STORY_ID" \
    "review_outcome" \
    "$decision" \
    "$RUN_ID" \
    "$branch_name" \
    "" \
    "$decision_source" \
    "$artifact_path" \
    "$status: $reason" || true

  if [[ "$decision" != "approve" ]]; then
    append_story_change_ledger_entry \
      "$STORY_ID" \
      "story_rejected" \
      "$decision" \
      "$RUN_ID" \
      "$branch_name" \
      "" \
      "$decision_source" \
      "$artifact_path" \
      "$reason" || true
  fi
}

[[ $# -eq 1 ]] || usage

STORY_ID="$1"
validate_story_id "$STORY_ID"

STORY_RUNS_ROOT="$RUNS_ROOT/$STORY_ID"
[[ -d "$STORY_RUNS_ROOT" ]] || fail "story run root not found for '$STORY_ID': $STORY_RUNS_ROOT"

LATEST_RUN_DIR="$(resolve_target_run_dir "$STORY_RUNS_ROOT" "$RUN_DIR_OVERRIDE")"
RUN_ID="$(basename "$LATEST_RUN_DIR")"
AI_REVIEW_FILE="$LATEST_RUN_DIR/$AI_REVIEW_FILE_NAME"
CLASSIFICATION_FILE="$LATEST_RUN_DIR/$CLASSIFICATION_FILE_NAME"
GATE_RESULT_FILE="$LATEST_RUN_DIR/$GATE_RESULT_FILE_NAME"
MANIFEST_FILE="$LATEST_RUN_DIR/manifest.md"

if working_tree_dirty; then
  fail_review_gate_dirty_working_tree "$STORY_ID" "$LATEST_RUN_DIR"
fi

reviewed_head="$(manifest_source_of_truth_head "$MANIFEST_FILE")"
checkout_head="$(current_checkout_head)"
head_status="$(head_consistency_status "$MANIFEST_FILE")"

case "$head_status" in
  mismatch:*)
    reason="Reviewed HEAD $reviewed_head does not match current checkout HEAD $checkout_head"
    decision_source="review_head_mismatch"
    ;;
  unknown:manifest_head_missing)
    reason="Run manifest is missing the reviewed HEAD contract"
    decision_source="review_head_missing"
    ;;
  unknown:current_head_unavailable:*)
    reason="Current checkout HEAD is unavailable for reviewed HEAD $reviewed_head"
    decision_source="checkout_head_unavailable"
    ;;
  *)
    reason=""
    decision_source=""
    ;;
esac

if [[ -n "$decision_source" ]]; then
  write_gate_result \
    "$GATE_RESULT_FILE" \
    "$STORY_ID" \
    "$RUN_ID" \
    "$LATEST_RUN_DIR" \
    "$AI_REVIEW_FILE" \
    "$CLASSIFICATION_FILE" \
    "$reviewed_head" \
    "$checkout_head" \
    "reject" \
    "$decision_source" \
    "failed" \
    "$reason"
  update_manifest_gate_artifacts "$MANIFEST_FILE" "$LATEST_RUN_DIR"
  append_review_ledger_events "reject" "$decision_source" "failed" "$reason"
  printf 'Review gate result written: %s\n' "$GATE_RESULT_FILE"
  printf 'Final decision: reject\n'
  printf 'Run analysis command: AUTOMATION_RUN_DIR=%q automation/scripts/analyze_story_run.sh %q\n' "$LATEST_RUN_DIR" "$STORY_ID"
  fail "review gate rejected merge for '$STORY_ID' ($reason)"
fi

fidelity_status="$(review_artifact_fidelity_status "$LATEST_RUN_DIR" "$MANIFEST_FILE")"
IFS=$'\t' read -r fidelity_decision fidelity_source fidelity_reason <<< "$fidelity_status"

if [[ "$fidelity_decision" == "reject" ]]; then
  write_gate_result \
    "$GATE_RESULT_FILE" \
    "$STORY_ID" \
    "$RUN_ID" \
    "$LATEST_RUN_DIR" \
    "$AI_REVIEW_FILE" \
    "$CLASSIFICATION_FILE" \
    "$reviewed_head" \
    "$checkout_head" \
    "reject" \
    "$fidelity_source" \
    "failed" \
    "$fidelity_reason"
  update_manifest_gate_artifacts "$MANIFEST_FILE" "$LATEST_RUN_DIR"
  append_review_ledger_events "reject" "$fidelity_source" "failed" "$fidelity_reason"
  printf 'Review gate result written: %s\n' "$GATE_RESULT_FILE"
  printf 'Final decision: reject\n'
  printf 'Run analysis command: AUTOMATION_RUN_DIR=%q automation/scripts/analyze_story_run.sh %q\n' "$LATEST_RUN_DIR" "$STORY_ID"
  fail "review gate rejected merge for '$STORY_ID' ($fidelity_reason)"
fi

set +e
AUTOMATION_RUN_DIR="$LATEST_RUN_DIR" "$AI_REVIEW_SCRIPT" "$STORY_ID"
ai_review_exit_code=$?
set -e
if [[ $ai_review_exit_code -ne 0 ]]; then
  write_gate_result \
    "$GATE_RESULT_FILE" \
    "$STORY_ID" \
    "$RUN_ID" \
    "$LATEST_RUN_DIR" \
    "$AI_REVIEW_FILE" \
    "$CLASSIFICATION_FILE" \
    "$reviewed_head" \
    "$checkout_head" \
    "reject" \
    "ai_review_failed" \
    "failed" \
    "AI review step failed"
  update_manifest_gate_artifacts "$MANIFEST_FILE" "$LATEST_RUN_DIR"
  append_review_ledger_events "reject" "ai_review_failed" "failed" "AI review step failed"
  fail "AI review step failed for '$STORY_ID' (exit $ai_review_exit_code)"
fi

require_file "$AI_REVIEW_FILE"

decision="reject"
status="failed"
decision_source="invalid_or_missing_merge_recommendation"
reason="Classification output did not contain a valid merge recommendation"

set +e
AUTOMATION_RUN_DIR="$LATEST_RUN_DIR" "$CLASSIFY_REVIEW_SCRIPT" "$STORY_ID"
classification_exit_code=$?
set -e

if [[ $classification_exit_code -eq 0 ]]; then
  if [[ -f "$CLASSIFICATION_FILE" ]]; then
    if merge_recommendation="$(extract_merge_recommendation "$CLASSIFICATION_FILE")"; then
      decision="$merge_recommendation"
      if [[ "$decision" == "approve" ]]; then
        status="passed"
        reason="Review classification approved merge"
      else
        reason="Review classification rejected merge"
      fi
      decision_source="review_classification"
    else
      decision_source="invalid_or_missing_merge_recommendation"
      reason="Review classification artifact did not contain a valid merge recommendation"
    fi
  else
    decision_source="review_classification_missing_artifact"
    reason="Review classification step exited successfully but did not write review_classification.md"
  fi
else
  if [[ -f "$CLASSIFICATION_FILE" ]]; then
    decision_source="invalid_or_missing_merge_recommendation"
    reason="Review classification artifact did not contain a valid merge recommendation"
  else
    decision_source="review_classification_failed"
    reason="Review classification step failed"
  fi
fi

write_gate_result \
  "$GATE_RESULT_FILE" \
  "$STORY_ID" \
  "$RUN_ID" \
  "$LATEST_RUN_DIR" \
  "$AI_REVIEW_FILE" \
  "$CLASSIFICATION_FILE" \
  "$reviewed_head" \
  "$checkout_head" \
  "$decision" \
  "$decision_source" \
  "$status" \
  "$reason"

update_manifest_gate_artifacts "$MANIFEST_FILE" "$LATEST_RUN_DIR"
append_review_ledger_events "$decision" "$decision_source" "$status" "$reason"
printf 'Review gate result written: %s\n' "$GATE_RESULT_FILE"
printf 'Final decision: %s\n' "$decision"
printf 'Run analysis command: AUTOMATION_RUN_DIR=%q automation/scripts/analyze_story_run.sh %q\n' "$LATEST_RUN_DIR" "$STORY_ID"

if [[ $classification_exit_code -ne 0 ]]; then
  fail "review classification step failed for '$STORY_ID' (exit $classification_exit_code); gate rejected"
fi

if [[ "$decision" != "approve" ]]; then
  fail "review gate rejected merge for '$STORY_ID' (decision: $decision, source: $decision_source)"
fi
