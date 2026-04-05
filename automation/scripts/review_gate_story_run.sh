#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${AUTOMATION_ROOT_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
RUNS_ROOT="${AUTOMATION_RUNS_ROOT:-$ROOT_DIR/automation/runs}"
RUN_DIR_OVERRIDE="${AUTOMATION_RUN_DIR:-}"
EPHEMERAL_LEDGER_PATH="automation/story_change_ledger.jsonl"
EPHEMERAL_LEDGER_EXCLUDE_PATHSPEC=":(exclude)$EPHEMERAL_LEDGER_PATH"

# shellcheck source=automation/scripts/merge_recommendation_contract.sh
source "$SCRIPT_DIR/merge_recommendation_contract.sh"
# shellcheck source=automation/scripts/story_change_ledger.sh
source "$SCRIPT_DIR/story_change_ledger.sh"

AI_REVIEW_FILE_NAME="ai_review_result.md"
AI_REVIEW_RAW_OUTPUT_FILE_NAME="ai_review_raw_output.txt"
CLASSIFICATION_FILE_NAME="review_classification.md"
GATE_RESULT_FILE_NAME="review_gate_result.json"
ESCALATION_RESULT_FILE_NAME="escalation_result.json"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

read_gate_json_field() {
  local json_file="$1"
  local key="$2"

  [[ -f "$json_file" ]] || return 1

  python3 - "$json_file" "$key" <<'PY'
import json, sys

path, key = sys.argv[1], sys.argv[2]

def no_dupes(pairs):
    d = {}
    for k, v in pairs:
        if k in d:
            raise ValueError("duplicate key")
        d[k] = v
    return d

with open(path, "r", encoding="utf-8") as f:
    data = json.load(f, object_pairs_hook=no_dupes)

if not isinstance(data, dict):
    raise ValueError("not object")

val = data.get(key, None)

if isinstance(val, str):
    print(val)
    sys.exit(0)

sys.exit(1)
PY
}

working_tree_dirty() {
  local status_output
  status_output="$(git -C "$ROOT_DIR" status --porcelain --untracked-files=normal -- . "$EPHEMERAL_LEDGER_EXCLUDE_PATHSPEC" 2>/dev/null || true)"
  [[ -n "$status_output" ]]
}

fail_review_gate_dirty_working_tree() {
  local story_id="$1"
  local run_dir="${2:-}"
  {
    printf "ERROR: review gate blocked for '%s'\n" "$story_id"
    printf 'Reason: workspace-only changes would make gate evaluation diverge from committed HEAD and origin/main...HEAD\n'
    printf 'Required action:\n'
    printf ' - inspect the workspace-only changes\n'
    printf ' - commit the changes if they belong in the reviewed diff, or discard them if they do not\n'
    printf ' - if you committed review-relevant changes, rerun automation/scripts/run_story.sh %s\n' "$story_id"
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

artifact_file_state() {
  local path="$1"

  if [[ ! -f "$path" ]]; then
    printf 'missing\n'
    return 0
  fi

  if [[ ! -s "$path" ]]; then
    printf 'empty\n'
    return 0
  fi

  printf 'present\n'
}

read_ai_review_artifact_state() {
  local review_file="$1"
  local raw_output_file="${2:-}"
  local prompt_file="${3:-}"

  python3 - "$review_file" "$raw_output_file" "$prompt_file" <<'PY'
import sys
from difflib import SequenceMatcher
from pathlib import Path

path = Path(sys.argv[1])
raw_path = Path(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] else None
prompt_path = Path(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3] else None

if not path.exists():
    if raw_path and raw_path.exists():
        print(
            f"invalid\tai_review_normalization_failed\tPinned normalized AI review artifact is missing while raw output exists at {raw_path}; rerun automation/scripts/ai_review_story_run.sh for this pinned run"
        )
    else:
        print("missing\tai_review_missing_artifact\trequired file not found")
    sys.exit(0)

try:
    text = path.read_text(encoding="utf-8")
except Exception:
    print(
        "invalid\tai_review_unreadable_artifact\tPinned AI review artifact could not be read as UTF-8 text; rerun automation/scripts/ai_review_story_run.sh for this pinned run"
    )
    sys.exit(0)
if not text.strip():
    print("invalid\tai_review_empty_artifact\tPinned AI review artifact is empty; rerun automation/scripts/ai_review_story_run.sh for this pinned run")
    sys.exit(0)

lines = text.splitlines()
normalized = [line.lstrip("\ufeff").strip() for line in lines]
first_nonempty_index = next((i for i, line in enumerate(normalized) if line), None)

if first_nonempty_index is None:
    print("invalid\tai_review_empty_artifact\tPinned AI review artifact is empty; rerun automation/scripts/ai_review_story_run.sh for this pinned run")
    sys.exit(0)

first_review_index = next((i for i, line in enumerate(normalized) if line == "# AI Review"), None)
first_result_index = next((i for i, line in enumerate(normalized) if line == "# AI Review Result"), None)

if first_review_index is None or first_result_index is None:
    print(
        "invalid\tai_review_normalization_failed\tPinned AI review artifact failed required structure validation; it must contain both '# AI Review' and '# AI Review Result'. Rerun automation/scripts/ai_review_story_run.sh for this pinned run"
    )
    sys.exit(0)

if first_review_index != first_nonempty_index or first_result_index <= first_review_index:
    print(
        "invalid\tai_review_normalization_failed\tPinned AI review artifact failed required structure validation; it must start with '# AI Review' and include '# AI Review Result' after it. Rerun automation/scripts/ai_review_story_run.sh for this pinned run"
    )
    sys.exit(0)

review_body = [line for line in normalized[first_review_index + 1:first_result_index] if line and not line.startswith("#")]
result_body = [line for line in normalized[first_result_index + 1:] if line and not line.startswith("#")]
if not review_body or not result_body:
    print(
        "invalid\tai_review_normalization_failed\tPinned AI review artifact failed required structure validation; it must include substantive content in both '# AI Review' and '# AI Review Result'. Rerun automation/scripts/ai_review_story_run.sh for this pinned run"
    )
    sys.exit(0)

if prompt_path and prompt_path.exists():
    try:
        prompt_text = prompt_path.read_text(encoding="utf-8")
    except Exception:
        prompt_text = ""

    if prompt_text.strip():
        review_norm = " ".join(text.split())
        prompt_norm = " ".join(prompt_text.split())
        if review_norm == prompt_norm:
            print(
                "invalid\tai_review_normalization_failed\tPinned AI review artifact matches the prompt content and appears to be prompt echo. Rerun automation/scripts/ai_review_story_run.sh for this pinned run"
            )
            sys.exit(0)
        similarity = SequenceMatcher(a=review_norm.lower(), b=prompt_norm.lower()).ratio()
        if len(review_norm) >= 200 and len(prompt_norm) >= 200 and similarity >= 0.92:
            print(
                "invalid\tai_review_normalization_failed\tPinned AI review artifact is too similar to the prompt content and appears to be prompt echo. Rerun automation/scripts/ai_review_story_run.sh for this pinned run"
            )
            sys.exit(0)

print("valid\tai_review_valid\tvalidated")
PY
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

json_bool() {
  if [[ "$1" == "true" ]]; then
    printf 'true'
  else
    printf 'false'
  fi
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

run_manifest_companion_filter_enabled() {
  local run_dir="$1"
  local manifest_file="$run_dir/manifest.md"
  local companion_filter_mode

  [[ -f "$manifest_file" ]] || return 1
  companion_filter_mode="$(manifest_value "$manifest_file" "execution_companion_filter_mode")"
  [[ "$companion_filter_mode" == "enabled" ]]
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
  local expected_diff_file expected_changed_files_file artifact_changed_files_file normalized_artifact_diff_file

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
  normalized_artifact_diff_file="$(mktemp)"

  if ! git -C "$ROOT_DIR" diff "$review_artifact_base" -- . "$EPHEMERAL_LEDGER_EXCLUDE_PATHSPEC" \
      | filter_review_fidelity_diff "$STORY_ID" "$run_dir" > "$expected_diff_file"; then
    rm -f "$expected_diff_file" "$expected_changed_files_file" "$artifact_changed_files_file" "$normalized_artifact_diff_file"
    printf 'reject\treview_diff_generation_failed\tunable to regenerate authoritative diff from review_artifact_base %s\n' "$review_artifact_base"
    return 0
  fi

  git -C "$ROOT_DIR" diff --name-only "$review_artifact_base" -- . "$EPHEMERAL_LEDGER_EXCLUDE_PATHSPEC" \
    | sed '/^$/d' \
    | filter_review_fidelity_paths "$STORY_ID" "$run_dir" "$expected_changed_files_file"

  if [[ $? -ne 0 ]]; then
    rm -f "$expected_diff_file" "$expected_changed_files_file" "$artifact_changed_files_file" "$normalized_artifact_diff_file"
    printf 'reject\treview_changed_files_generation_failed\tunable to regenerate authoritative changed_files from review_artifact_base %s\n' "$review_artifact_base"
    return 0
  fi
  
  if ! filter_review_fidelity_diff "$STORY_ID" "$run_dir" < "$diff_artifact" > "$normalized_artifact_diff_file"; then
    rm -f "$expected_diff_file" "$expected_changed_files_file" "$artifact_changed_files_file" "$normalized_artifact_diff_file"
    printf 'reject\treview_diff_artifact_invalid\treview artifact diff.patch could not be normalized for fidelity comparison; rerun automation/scripts/run_story.sh %s\n' "$STORY_ID"
    return 0
  fi

  sorted_changed_files_to "$STORY_ID" "$run_dir" "$changed_files_artifact" "$artifact_changed_files_file"

  if ! cmp -s "$artifact_changed_files_file" "$expected_changed_files_file"; then
    rm -f "$expected_diff_file" "$expected_changed_files_file" "$artifact_changed_files_file" "$normalized_artifact_diff_file"
    printf 'reject\treview_changed_files_mismatch\treview artifact changed_files.txt is stale or inconsistent with current HEAD diff; rerun automation/scripts/run_story.sh %s\n' "$STORY_ID"
    return 0
  fi

  if ! cmp -s "$normalized_artifact_diff_file" "$expected_diff_file"; then
    rm -f "$expected_diff_file" "$expected_changed_files_file" "$artifact_changed_files_file" "$normalized_artifact_diff_file"
    printf 'reject\treview_diff_patch_mismatch\treview artifact diff.patch is stale or inconsistent with current HEAD diff; rerun automation/scripts/run_story.sh %s\n' "$STORY_ID"
    return 0
  fi

  rm -f "$expected_diff_file" "$expected_changed_files_file" "$artifact_changed_files_file" "$normalized_artifact_diff_file"
  printf 'ok\treview_artifact_fidelity_valid\tartifact fidelity verified against review_artifact_base %s\n' "$review_artifact_base"
}

review_input_artifact_status() {
  local ai_review_file="$1"
  local ai_review_raw_output_file="$2"
  local ai_review_prompt_file="$3"
  local classification_file="$4"
  local ai_review_state classification_state merge_recommendation validation_state validation_status validation_code validation_reason

  ai_review_state="$(artifact_file_state "$ai_review_file")"
  case "$ai_review_state" in
    missing)
      if [[ -f "$ai_review_raw_output_file" ]]; then
        printf 'reject\tai_review_normalization_failed\tPinned normalized AI review artifact is missing while raw output exists at %s; rerun automation/scripts/ai_review_story_run.sh %s for this pinned run\n' "$ai_review_raw_output_file" "$STORY_ID"
      else
        printf 'reject\tai_review_missing_artifact\tPinned AI review artifact is missing; run automation/scripts/ai_review_story_run.sh %s for this pinned run first\n' "$STORY_ID"
      fi
      return 0
      ;;
    empty)
      printf 'reject\tai_review_invalid_artifact\tPinned AI review artifact is empty; rerun automation/scripts/ai_review_story_run.sh %s for this pinned run\n' "$STORY_ID"
      return 0
      ;;
  esac

  validation_state="$(read_ai_review_artifact_state "$ai_review_file" "$ai_review_raw_output_file" "$ai_review_prompt_file")"
  IFS=$'\t' read -r validation_status validation_code validation_reason <<< "$validation_state"
  if [[ "$validation_status" != "valid" ]]; then
    printf 'reject\t%s\t%s\n' "$validation_code" "$validation_reason"
    return 0
  fi

  classification_state="$(artifact_file_state "$classification_file")"
  case "$classification_state" in
    missing)
      printf 'reject\treview_classification_missing_artifact\tPinned review classification artifact is missing; run automation/scripts/classify_review_story_run.sh %s for this pinned run first\n' "$STORY_ID"
      return 0
      ;;
    empty)
      printf 'reject\treview_classification_invalid_artifact\tPinned review classification artifact is empty; rerun automation/scripts/classify_review_story_run.sh %s for this pinned run\n' "$STORY_ID"
      return 0
      ;;
  esac

  if merge_recommendation="$(extract_merge_recommendation "$classification_file" 2>/dev/null)"; then
    if [[ "$merge_recommendation" == "approve" ]]; then
      printf 'approve\treview_classification\tReview classification approved merge\n'
    else
      printf 'reject\treview_classification\tReview classification rejected merge\n'
    fi
    return 0
  fi

  printf 'reject\tinvalid_or_missing_merge_recommendation\tReview classification artifact did not contain a valid merge recommendation\n'
}

extract_markdown_section_items() {
  local file="$1"
  local heading_kind="$2"

  [[ -f "$file" ]] || return 0

  awk -v heading_kind="$heading_kind" '
    function is_target_heading(line, kind) {
      if (kind == "allowed") {
        return line == "## Files Allowed To Change"
      }
      if (kind == "blocked") {
        return line == "## Files Not Allowed To Change"
      }
      return 0
    }

    BEGIN {
      in_section = 0
    }

    /^## / {
      if (is_target_heading($0, heading_kind)) {
        in_section = 1
        next
      }
      if (in_section) {
        exit
      }
    }

    in_section && /^[[:space:]]*[-*][[:space:]]+/ {
      item = $0
      sub(/^[[:space:]]*[-*][[:space:]]+/, "", item)
      gsub(/`/, "", item)
      print item
    }
  ' "$file"
}

is_execution_companion_artifact_path() {
  local run_dir="$1"
  local path="$2"

  run_manifest_companion_filter_enabled "$run_dir" || return 1

  case "$path" in
    docs/90_codex/epics/US-AUTO_REGISTRY.md)
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

  is_execution_companion_artifact_path "$run_dir" "$path"
}

is_story_artifact_review_ignored_path() {
  local story_id="$1"
  local path="$2"

  [[ "$path" == "automation/bundle_packs/$story_id.bundle.md" ]] && return 0
  [[ "$path" == "automation/bundles/active/$story_id" ]] && return 0
  [[ "$path" == automation/bundles/active/$story_id/* ]] && return 0

  return 1
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
      else
        skip=0
      fi
    fi

    if [[ "${skip:-0}" == "1" ]]; then
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

sorted_effective_changed_files_for_run_to() {
  local story_id="$1"
  local run_dir="$2"
  local output_file="$3"
  local changed_files_file="$run_dir/changed_files.txt"

  if run_manifest_companion_filter_enabled "$run_dir"; then
    recompute_filtered_changed_files_for_run_to "$story_id" "$run_dir" "$output_file" || return 1
    return 0
  fi

  [[ -f "$changed_files_file" ]] || return 1
  sorted_changed_files_to "$story_id" "$run_dir" "$changed_files_file" "$output_file"
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

effective_diff_patch_for_run_to() {
  local story_id="$1"
  local run_dir="$2"
  local output_file="$3"
  local diff_artifact="$run_dir/diff.patch"

  if run_manifest_companion_filter_enabled "$run_dir"; then
    recompute_filtered_diff_patch_for_run_to "$story_id" "$run_dir" "$output_file" || return 1
    return 0
  fi

  [[ -f "$diff_artifact" ]] || return 1
  filter_review_fidelity_diff "$story_id" "$run_dir" < "$diff_artifact" > "$output_file"
}

run_has_nonempty_changed_files() {
  local run_dir="$1"
  local filtered_changed_files_file

  filtered_changed_files_file="$(mktemp)"
  sorted_effective_changed_files_for_run_to "$STORY_ID" "$run_dir" "$filtered_changed_files_file" || {
    rm -f "$filtered_changed_files_file"
    return 1
  }
  if [[ -n "$(sed '/^[[:space:]]*$/d' "$filtered_changed_files_file")" ]]; then
    rm -f "$filtered_changed_files_file"
    return 0
  fi
  rm -f "$filtered_changed_files_file"
  return 1
}

run_has_non_converging_evidence() {
  local run_dir="$1"
  local manifest_file="$run_dir/manifest.md"
  local codex_exit_code materialization_status pytest_exit_code changed_files_detected

  [[ -f "$manifest_file" ]] || return 1

  codex_exit_code="$(manifest_value "$manifest_file" "codex_exit_code")"
  pytest_exit_code="$(manifest_value "$manifest_file" "pytest_exit_code")"
  materialization_status="$(manifest_value "$manifest_file" "materialization_status")"
  changed_files_detected="$(manifest_value "$manifest_file" "changed_files_detected")"

  [[ "$codex_exit_code" == "0" ]] || return 1
  [[ "$pytest_exit_code" == "0" ]] || return 1
  [[ "$changed_files_detected" == "yes" ]] || return 1
  [[ "$materialization_status" == "applied" || "$materialization_status" == "not_needed" ]] || return 1
  run_has_nonempty_changed_files "$run_dir" || return 1
}

resolve_previous_run_dir() {
  local story_runs_root="$1"
  local target_run_dir="$2"
  local previous_run_dir=""
  local candidate_run_dir

  while IFS= read -r candidate_run_dir; do
    [[ "$candidate_run_dir" == "$target_run_dir" ]] && break
    previous_run_dir="$candidate_run_dir"
  done < <(find "$story_runs_root" -mindepth 1 -maxdepth 1 -type d -print | LC_ALL=C sort)

  [[ -n "$previous_run_dir" ]] || return 1
  printf '%s\n' "$previous_run_dir"
}

detect_non_converging_rerun_for_run() {
  local story_runs_root="$1"
  local current_run_dir="$2"
  local previous_run_dir previous_head latest_head
  local current_changed_files_sorted previous_changed_files_sorted
  local current_diff previous_diff

  previous_run_dir="$(resolve_previous_run_dir "$story_runs_root" "$current_run_dir" || true)"
  [[ -n "$previous_run_dir" ]] || return 1

  run_has_non_converging_evidence "$previous_run_dir" || return 1
  run_has_non_converging_evidence "$current_run_dir" || return 1

  previous_head="$(manifest_source_of_truth_head "$previous_run_dir/manifest.md")"
  latest_head="$(manifest_source_of_truth_head "$current_run_dir/manifest.md")"

  [[ "$previous_head" =~ ^[0-9a-f]{40}$ ]] || return 1
  [[ "$latest_head" =~ ^[0-9a-f]{40}$ ]] || return 1
  [[ "$previous_head" != "$latest_head" ]] || return 1

  current_changed_files_sorted="$(mktemp)"
  previous_changed_files_sorted="$(mktemp)"
  current_diff="$(mktemp)"
  previous_diff="$(mktemp)"
  sorted_effective_changed_files_for_run_to "$STORY_ID" "$current_run_dir" "$current_changed_files_sorted" || {
    rm -f "$current_changed_files_sorted" "$previous_changed_files_sorted" "$current_diff" "$previous_diff"
    return 1
  }
  sorted_effective_changed_files_for_run_to "$STORY_ID" "$previous_run_dir" "$previous_changed_files_sorted" || {
    rm -f "$current_changed_files_sorted" "$previous_changed_files_sorted" "$current_diff" "$previous_diff"
    return 1
  }

  cmp -s "$current_changed_files_sorted" "$previous_changed_files_sorted" || {
    rm -f "$current_changed_files_sorted" "$previous_changed_files_sorted" "$current_diff" "$previous_diff"
    return 1
  }

  if run_manifest_companion_filter_enabled "$current_run_dir" || run_manifest_companion_filter_enabled "$previous_run_dir"; then
    effective_diff_patch_for_run_to "$STORY_ID" "$current_run_dir" "$current_diff" || {
      rm -f "$current_changed_files_sorted" "$previous_changed_files_sorted" "$current_diff" "$previous_diff"
      return 1
    }
    effective_diff_patch_for_run_to "$STORY_ID" "$previous_run_dir" "$previous_diff" || {
      rm -f "$current_changed_files_sorted" "$previous_changed_files_sorted" "$current_diff" "$previous_diff"
      return 1
    }
    cmp -s "$current_diff" "$previous_diff" || {
      rm -f "$current_changed_files_sorted" "$previous_changed_files_sorted" "$current_diff" "$previous_diff"
      return 1
    }
  fi

  rm -f "$current_changed_files_sorted" "$previous_changed_files_sorted" "$current_diff" "$previous_diff"
  printf '%s\n' "$previous_run_dir"
  return 0
}

strict_manual_finish_continuation_allowed() {
  local story_runs_root="$1"
  local current_run_dir="$2"
  local reviewed_head="$3"
  local checkout_head="$4"
  local previous_non_converging_run_dir parent_head

  [[ -n "$reviewed_head" ]] || return 1
  [[ -n "$checkout_head" ]] || return 1
  [[ "$reviewed_head" != "$checkout_head" ]] || return 1

  previous_non_converging_run_dir="$(detect_non_converging_rerun_for_run "$story_runs_root" "$current_run_dir" || true)"
  [[ -n "$previous_non_converging_run_dir" ]] || return 1

  parent_head="$(git -C "$ROOT_DIR" rev-parse --verify "${checkout_head}^" 2>/dev/null || true)"
  [[ -n "$parent_head" ]] || return 1

  [[ "$parent_head" == "$reviewed_head" ]]
}

resolve_review_head_contract() {
  local story_runs_root="$1"
  local current_run_dir="$2"
  local manifest_file="$3"
  local manifest_reviewed_head checkout_head

  manifest_reviewed_head="$(manifest_source_of_truth_head "$manifest_file")"
  if [[ -z "$manifest_reviewed_head" ]]; then
    printf 'reject\x1freview_head_missing\x1fRun manifest is missing the reviewed HEAD contract\x1f\x1f\x1fpinned_run_manifest\n'
    return 0
  fi

  checkout_head="$(current_checkout_head)"
  if [[ -z "$checkout_head" ]]; then
    printf 'reject\x1fcheckout_head_unavailable\x1fCurrent checkout HEAD is unavailable for reviewed HEAD %s\x1f\x1f%s\x1fpinned_run_manifest\n' \
      "$manifest_reviewed_head" \
      "$manifest_reviewed_head"
    return 0
  fi

  if head_matches_expected "$manifest_reviewed_head" "$checkout_head"; then
    printf 'allow\x1freview_head_match\x1fvalidated\x1f%s\x1f%s\x1fcommitted_head_match\n' \
      "$checkout_head" \
      "$manifest_reviewed_head"
    return 0
  fi

  if strict_manual_finish_continuation_allowed "$story_runs_root" "$current_run_dir" "$manifest_reviewed_head" "$checkout_head"; then
    printf 'allow\x1fmanual_finish_continuation_valid\x1fvalidated\x1f%s\x1f%s\x1fmanual_finish_continuation\n' \
      "$checkout_head" \
      "$manifest_reviewed_head"
    return 0
  fi

  printf 'reject\x1freview_head_mismatch\x1fReviewed HEAD %s does not match current checkout HEAD %s\x1f\x1f%s\x1fpinned_run_manifest\n' \
    "$manifest_reviewed_head" \
    "$checkout_head" \
    "$manifest_reviewed_head"
}

find_previous_reject_stagnation_run() {
  local story_runs_root="$1"
  local current_run_dir="$2"
  local current_diff="$3"
  local current_changed_files="$4"
  local current_run_id
  local candidate_run_dir candidate_gate_result candidate_decision candidate_source candidate_id
  local previous_changed_files_sorted current_changed_files_sorted
  local normalized_current_diff normalized_candidate_diff

  current_run_id="$(basename "$current_run_dir")"

  current_changed_files_sorted="$(mktemp)"
  sorted_effective_changed_files_for_run_to "$STORY_ID" "$current_run_dir" "$current_changed_files_sorted" || {
    rm -f "$current_changed_files_sorted"
    return 1
  }
  normalized_current_diff="$(mktemp)"
  effective_diff_patch_for_run_to "$STORY_ID" "$current_run_dir" "$normalized_current_diff" || {
    rm -f "$current_changed_files_sorted" "$normalized_current_diff"
    return 1
  }

  while IFS= read -r candidate_run_dir; do
    [[ -n "$candidate_run_dir" ]] || continue
    [[ "$candidate_run_dir" == "$current_run_dir" ]] && continue

    candidate_gate_result="$candidate_run_dir/$GATE_RESULT_FILE_NAME"
    [[ -f "$candidate_gate_result" ]] || continue

    candidate_decision="$(read_gate_json_field "$candidate_gate_result" "decision" 2>/dev/null || true)"
    candidate_source="$(read_gate_json_field "$candidate_gate_result" "decision_source" 2>/dev/null || true)"

    [[ "$candidate_decision" == "reject" ]] || continue
    [[ "$candidate_source" == "review_classification" ]] || continue
    [[ -f "$candidate_run_dir/diff.patch" ]] || continue
    [[ -f "$candidate_run_dir/changed_files.txt" ]] || continue

    normalized_candidate_diff="$(mktemp)"
    effective_diff_patch_for_run_to "$STORY_ID" "$candidate_run_dir" "$normalized_candidate_diff" || {
      rm -f "$normalized_candidate_diff"
      continue
    }

    if ! cmp -s "$normalized_current_diff" "$normalized_candidate_diff"; then
      rm -f "$normalized_candidate_diff"
      continue
    fi
    rm -f "$normalized_candidate_diff"

    previous_changed_files_sorted="$(mktemp)"
    sorted_effective_changed_files_for_run_to "$STORY_ID" "$candidate_run_dir" "$previous_changed_files_sorted" || {
      rm -f "$previous_changed_files_sorted"
      continue
    }
    if cmp -s "$current_changed_files_sorted" "$previous_changed_files_sorted"; then
      rm -f "$previous_changed_files_sorted" "$current_changed_files_sorted"
      rm -f "$normalized_current_diff"
      printf '%s\n' "$candidate_run_dir"
      return 0
    fi
    rm -f "$previous_changed_files_sorted"
  done < <(
    find "$story_runs_root" -mindepth 1 -maxdepth 1 -type d -print \
      | while IFS= read -r dir; do
          candidate_id="$(basename "$dir")"
          if [[ "$candidate_id" < "$current_run_id" ]]; then
            printf '%s\n' "$dir"
          fi
        done \
      | LC_ALL=C sort -r
  )

  rm -f "$current_changed_files_sorted" "$normalized_current_diff"
  return 1
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
  local manifest_reviewed_head="$9"
  local review_head_mode="${10}"
  local decision="${11}"
  local decision_source="${12}"
  local status="${13}"
  local reason="${14}"
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
  "manifest_reviewed_head": "$(json_escape "$manifest_reviewed_head")",
  "review_head_mode": "$(json_escape "$review_head_mode")",
  "decision": "$(json_escape "$decision")",
  "status": "$(json_escape "$status")",
  "decision_source": "$(json_escape "$decision_source")",
  "reason": "$(json_escape "$reason")"
}
EOF
  mv "$tmp_file" "$gate_result_file"
}

write_escalation_result() {
  local escalation_result_file="$1"
  local story_id="$2"
  local run_id="$3"
  local run_dir="$4"
  local gate_result_file="$5"
  local previous_run_id="$6"
  local status="$7"
  local reason="$8"
  local resolution_action="${9:-}"
  local resolved_at="${10:-}"
  local tmp_file

  tmp_file="$(mktemp "${escalation_result_file}.tmp.XXXXXX")"

  cat >"$tmp_file" <<EOF
{
  "story_id": "$(json_escape "$story_id")",
  "run_id": "$(json_escape "$run_id")",
  "run_dir": "$(json_escape "$run_dir")",
  "gate_result": "$(json_escape "$gate_result_file")",
  "decision_source": "repeated_reject_stagnation",
  "escalation_required": $(json_bool true),
  "status": "$(json_escape "$status")",
  "reason": "$(json_escape "$reason")",
  "previous_reject_run_id": "$(json_escape "$previous_run_id")",
  "resolution_action": "$(json_escape "$resolution_action")",
  "resolved_at": "$(json_escape "$resolved_at")"
}
EOF
  mv "$tmp_file" "$escalation_result_file"
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
    "review_gate_result.json" \
    "escalation_result.json"
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

maybe_write_escalation_result() {
  local run_dir="$1"
  local decision="$2"
  local decision_source="$3"
  local escalation_result_file="$run_dir/$ESCALATION_RESULT_FILE_NAME"
  local previous_run_dir previous_run_id escalation_reason

  [[ "$decision" == "reject" ]] || return 0
  [[ "$decision_source" == "review_classification" ]] || return 0
  [[ -f "$run_dir/diff.patch" ]] || return 0
  [[ -f "$run_dir/changed_files.txt" ]] || return 0

  if previous_run_dir="$(find_previous_reject_stagnation_run "$STORY_RUNS_ROOT" "$run_dir" "$run_dir/diff.patch" "$run_dir/changed_files.txt")"; then
    previous_run_id="$(basename "$previous_run_dir")"
    escalation_reason="Repeated review_classification reject with identical diff.patch and changed_files.txt as run $previous_run_id"
    write_escalation_result \
      "$escalation_result_file" \
      "$STORY_ID" \
      "$RUN_ID" \
      "$run_dir" \
      "$GATE_RESULT_FILE" \
      "$previous_run_id" \
      "pending" \
      "$escalation_reason"
    update_manifest_gate_artifacts "$MANIFEST_FILE" "$LATEST_RUN_DIR"
    printf 'Escalation required: %s\n' "$escalation_reason"
    printf 'Escalation command: AUTOMATION_RUN_DIR=%q automation/scripts/escalate_story.sh %q %s\n' "$LATEST_RUN_DIR" "$STORY_ID" "<accept-as-is|force-followup|abort>"
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
AI_REVIEW_RAW_OUTPUT_FILE="$LATEST_RUN_DIR/$AI_REVIEW_RAW_OUTPUT_FILE_NAME"
AI_REVIEW_PROMPT_FILE="$LATEST_RUN_DIR/chatgpt_review_prompt.md"
CLASSIFICATION_FILE="$LATEST_RUN_DIR/$CLASSIFICATION_FILE_NAME"
GATE_RESULT_FILE="$LATEST_RUN_DIR/$GATE_RESULT_FILE_NAME"
MANIFEST_FILE="$LATEST_RUN_DIR/manifest.md"

if working_tree_dirty; then
  fail_review_gate_dirty_working_tree "$STORY_ID" "$LATEST_RUN_DIR"
fi

reviewed_head="$(manifest_source_of_truth_head "$MANIFEST_FILE")"
checkout_head="$(current_checkout_head)"
manifest_reviewed_head="$reviewed_head"
review_head_mode="pinned_run_manifest"
head_status="$(head_consistency_status "$MANIFEST_FILE")"
head_contract_state="$(resolve_review_head_contract "$STORY_RUNS_ROOT" "$LATEST_RUN_DIR" "$MANIFEST_FILE")"
IFS=$'\x1f' read -r head_contract_status head_contract_code head_contract_reason effective_reviewed_head contract_manifest_reviewed_head contract_review_head_mode <<< "$head_contract_state"
manual_finish_continuation_allowed="false"

if [[ "$head_contract_code" == "manual_finish_continuation_valid" ]]; then
  manual_finish_continuation_allowed="true"
fi
if [[ -n "$effective_reviewed_head" ]]; then
  reviewed_head="$effective_reviewed_head"
fi
if [[ -n "$contract_manifest_reviewed_head" ]]; then
  manifest_reviewed_head="$contract_manifest_reviewed_head"
fi
if [[ -n "$contract_review_head_mode" ]]; then
  review_head_mode="$contract_review_head_mode"
fi

case "$head_status" in
  mismatch:*)
    if [[ "$manual_finish_continuation_allowed" == "true" ]]; then
      reason=""
      decision_source=""
    else
      reason="Reviewed HEAD $reviewed_head does not match current checkout HEAD $checkout_head"
      decision_source="review_head_mismatch"
    fi
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

if [[ "$head_contract_status" == "reject" ]]; then
  reason="$head_contract_reason"
  decision_source="$head_contract_code"
fi

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
    "$manifest_reviewed_head" \
    "$review_head_mode" \
    "reject" \
    "$decision_source" \
    "failed" \
    "$reason"
  update_manifest_gate_artifacts "$MANIFEST_FILE" "$LATEST_RUN_DIR"
  append_review_ledger_events "reject" "$decision_source" "failed" "$reason"
  maybe_write_escalation_result "$LATEST_RUN_DIR" "reject" "$decision_source"
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
    "$manifest_reviewed_head" \
    "$review_head_mode" \
    "reject" \
    "$fidelity_source" \
    "failed" \
    "$fidelity_reason"
  update_manifest_gate_artifacts "$MANIFEST_FILE" "$LATEST_RUN_DIR"
  append_review_ledger_events "reject" "$fidelity_source" "failed" "$fidelity_reason"
  maybe_write_escalation_result "$LATEST_RUN_DIR" "reject" "$fidelity_source"
  printf 'Review gate result written: %s\n' "$GATE_RESULT_FILE"
  printf 'Final decision: reject\n'
  printf 'Run analysis command: AUTOMATION_RUN_DIR=%q automation/scripts/analyze_story_run.sh %q\n' "$LATEST_RUN_DIR" "$STORY_ID"
  fail "review gate rejected merge for '$STORY_ID' ($fidelity_reason)"
fi

input_status="$(review_input_artifact_status "$AI_REVIEW_FILE" "$AI_REVIEW_RAW_OUTPUT_FILE" "$AI_REVIEW_PROMPT_FILE" "$CLASSIFICATION_FILE")"
IFS=$'\t' read -r decision decision_source reason <<< "$input_status"
status="failed"
if [[ "$decision" == "approve" ]]; then
  status="passed"
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
  "$manifest_reviewed_head" \
  "$review_head_mode" \
  "$decision" \
  "$decision_source" \
  "$status" \
  "$reason"

update_manifest_gate_artifacts "$MANIFEST_FILE" "$LATEST_RUN_DIR"
append_review_ledger_events "$decision" "$decision_source" "$status" "$reason"
maybe_write_escalation_result "$LATEST_RUN_DIR" "$decision" "$decision_source"
printf 'Review gate result written: %s\n' "$GATE_RESULT_FILE"
printf 'Final decision: %s\n' "$decision"
printf 'Run analysis command: AUTOMATION_RUN_DIR=%q automation/scripts/analyze_story_run.sh %q\n' "$LATEST_RUN_DIR" "$STORY_ID"

if [[ "$decision" != "approve" ]]; then
  fail "review gate rejected merge for '$STORY_ID' (decision: $decision, source: $decision_source)"
fi
