#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${AUTOMATION_ROOT_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
RUNS_ROOT="${AUTOMATION_RUNS_ROOT:-$ROOT_DIR/automation/runs}"
RUN_DIR_OVERRIDE="${AUTOMATION_RUN_DIR:-}"
STORY_ID=""
STAGE_LOOP_CAP_THRESHOLD="${STAGE_LOOP_CAP_THRESHOLD:-3}"
EPHEMERAL_LEDGER_PATH="automation/story_change_ledger.jsonl"
EPHEMERAL_LEDGER_EXCLUDE_PATHSPEC=":(exclude)$EPHEMERAL_LEDGER_PATH"

# shellcheck source=automation/scripts/merge_recommendation_contract.sh
source "$SCRIPT_DIR/merge_recommendation_contract.sh"
# shellcheck source=automation/scripts/story_stage_loop.sh
source "$SCRIPT_DIR/story_stage_loop.sh"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

usage() {
  cat >&2 <<'EOF'
Usage:
  AUTOMATION_RUN_DIR=automation/runs/STORY_ID/RUN_DIR automation/scripts/analyze_story_run.sh STORY_ID

Example:
  AUTOMATION_RUN_DIR=automation/runs/US-AUTO-19/2026-03-16_11-00-00 automation/scripts/analyze_story_run.sh US-AUTO-19

Notes:
  - Pass STORY_ID as the only positional argument.
  - Pass the run directory through AUTOMATION_RUN_DIR when you need a pinned run.
  - Do not pass RUN_DIR as a second positional argument.
EOF
  exit 1
}

validate_story_id() {
  local story_id="$1"
  [[ "$story_id" =~ ^US-[A-Z0-9]+(-[A-Z0-9]+)*$ ]] || \
    fail "invalid STORY_ID '$story_id' (expected format like US-AUTO-19)"
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

list_story_run_dirs() {
  local story_runs_root="$1"

  find "$story_runs_root" -mindepth 1 -maxdepth 1 -type d -print | LC_ALL=C sort
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

manifest_value() {
  local manifest_file="$1"
  local key="$2"
  [[ -f "$manifest_file" ]] || return 0

  sed -n -E "s/^-[[:space:]]+${key}:[[:space:]]*(.*)$/\\1/p" "$manifest_file" | head -n 1
}

json_value() {
  local json_file="$1"
  local key="$2"
  [[ -f "$json_file" ]] || return 0

  sed -n -E "s/.*\"${key}\"[[:space:]]*:[[:space:]]*\"([^\"]*)\".*/\\1/p" "$json_file" | head -n 1
}

json_bool_value() {
  local json_file="$1"
  local key="$2"
  [[ -f "$json_file" ]] || return 0

  sed -n -E "s/.*\"${key}\"[[:space:]]*:[[:space:]]*(true|false).*/\\1/p" "$json_file" | head -n 1
}

read_refresh_evidence_metadata_state() {
  local run_dir="$1"
  local story_id="$2"
  local manifest_file="$run_dir/manifest.md"
  local metadata_file="$run_dir/refresh_review_evidence.json"
  local refresh_mode

  refresh_mode="$(manifest_value "$manifest_file" "refresh_mode")"
  if [[ -z "$refresh_mode" ]]; then
    printf 'not_refresh\t-\t-\n'
    return 0
  fi

  [[ -f "$metadata_file" ]] || {
    printf 'invalid\trefresh_metadata_missing\trefresh run metadata file is missing\n'
    return 0
  }

  python3 - "$metadata_file" "$story_id" "$refresh_mode" <<'PY'
import json
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
expected_story_id = sys.argv[2]
expected_mode = sys.argv[3]

try:
    def no_dupes(pairs):
        data = {}
        for key, value in pairs:
            if key in data:
                raise ValueError(f"duplicate key: {key}")
            data[key] = value
        return data

    payload = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=no_dupes)
except Exception as exc:
    print(f"invalid\trefresh_metadata_invalid_json\tinvalid refresh metadata JSON: {exc}")
    sys.exit(0)

if not isinstance(payload, dict):
    print("invalid\trefresh_metadata_invalid_payload\trefresh metadata must be a JSON object")
    sys.exit(0)

if payload.get("story_id") != expected_story_id:
    print("invalid\trefresh_story_mismatch\trefresh metadata story_id does not match requested story")
    sys.exit(0)

if payload.get("refresh_mode") != expected_mode:
    print("invalid\trefresh_mode_mismatch\trefresh metadata refresh_mode does not match manifest refresh_mode")
    sys.exit(0)

if payload.get("codex_invoked") is not False:
    print("invalid\trefresh_codex_invocation_invalid\trefresh metadata must record codex_invoked=false")
    sys.exit(0)

current_head = payload.get("current_head")
if not isinstance(current_head, str) or not re.fullmatch(r"[0-9a-f]{40}", current_head):
    print("invalid\trefresh_head_invalid\trefresh metadata current_head must be a full commit SHA")
    sys.exit(0)

if not isinstance(payload.get("generated_at"), str) or not payload["generated_at"].strip():
    print("invalid\trefresh_generated_at_missing\trefresh metadata generated_at is required")
    sys.exit(0)

evidence_paths = payload.get("evidence_paths")
if not isinstance(evidence_paths, dict):
    print("invalid\trefresh_evidence_paths_missing\trefresh metadata evidence_paths is required")
    sys.exit(0)

for key in ("run_dir", "changed_files", "diff_patch", "manifest"):
    value = evidence_paths.get(key)
    if not isinstance(value, str) or not value.strip():
        print(f"invalid\trefresh_evidence_path_missing\trefresh metadata evidence_paths.{key} is required")
        sys.exit(0)

serialized_paths = "\n".join(str(value) for value in evidence_paths.values())
required_artifacts = [
    "manifest.md",
    "changed_files.txt",
    "diff.patch",
    "review_bundle.md",
    "chatgpt_review_prompt.md",
    "pytest.txt",
    "refresh_review_evidence.json",
]

for artifact_name in required_artifacts:
    if artifact_name not in serialized_paths:
        print(
            "invalid\trefresh_evidence_path_missing\t"
            f"refresh metadata evidence_paths missing {artifact_name}"
        )
        sys.exit(0)

print("valid\trefresh_metadata_valid\tvalidated")
PY
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
            f"invalid\tai_review_normalization_failed\tNormalized AI review artifact is missing while raw output exists at {raw_path}"
        )
    else:
        print("missing\tai_review_missing_artifact\trequired file not found")
    sys.exit(0)

try:
    text = path.read_text(encoding="utf-8")
except Exception:
    print("invalid\tai_review_unreadable_artifact\tAI review artifact could not be read as UTF-8 text")
    sys.exit(0)
if not text.strip():
    print("invalid\tai_review_empty_artifact\tAI review artifact is empty")
    sys.exit(0)

lines = text.splitlines()
normalized = [line.lstrip("\ufeff").strip() for line in lines]
first_nonempty_index = next((i for i, line in enumerate(normalized) if line), None)

if first_nonempty_index is None:
    print("invalid\tai_review_empty_artifact\tAI review artifact is empty")
    sys.exit(0)

first_review_index = next((i for i, line in enumerate(normalized) if line == "# AI Review"), None)
first_result_index = next((i for i, line in enumerate(normalized) if line == "# AI Review Result"), None)

if first_review_index is None or first_result_index is None:
    print(
        "invalid\tai_review_normalization_failed\tAI review artifact failed required structure validation; it must contain both '# AI Review' and '# AI Review Result' sections"
    )
    sys.exit(0)

if first_review_index != first_nonempty_index or first_result_index <= first_review_index:
    print(
        "invalid\tai_review_normalization_failed\tAI review artifact failed required structure validation; it must start with '# AI Review' and include '# AI Review Result' after it"
    )
    sys.exit(0)

review_body = [line for line in normalized[first_review_index + 1:first_result_index] if line and not line.startswith("#")]
result_body = [line for line in normalized[first_result_index + 1:] if line and not line.startswith("#")]
if not review_body or not result_body:
    print(
        "invalid\tai_review_normalization_failed\tAI review artifact failed required structure validation; it must include substantive content in both '# AI Review' and '# AI Review Result' sections"
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
                "invalid\tai_review_normalization_failed\tAI review artifact matches the prompt content and appears to be prompt echo"
            )
            sys.exit(0)
        similarity = SequenceMatcher(a=review_norm.lower(), b=prompt_norm.lower()).ratio()
        if len(review_norm) >= 200 and len(prompt_norm) >= 200 and similarity >= 0.92:
            print(
                "invalid\tai_review_normalization_failed\tAI review artifact is too similar to the prompt content and appears to be prompt echo"
            )
            sys.exit(0)

print("valid\tai_review_valid\tvalidated")
PY
}


read_escalation_artifact_state() {
  local json_file="$1"
  [[ -f "$json_file" ]] || return 0

  python3 - "$json_file" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])

try:
    def reject_dupes(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError(f"duplicate key: {key}")
            out[key] = value
        return out

    data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_dupes)
except Exception:
    print("false\x1f\x1f\x1f\x1f\x1f")
    sys.exit(0)

if not isinstance(data, dict):
    print("false\x1f\x1f\x1f\x1f\x1f")
    sys.exit(0)

required = data.get("escalation_required")
status = data.get("status")
decision_source = data.get("decision_source")
reason = data.get("reason")
resolution_action = data.get("resolution_action")

if not isinstance(required, bool) or not isinstance(status, str) or not isinstance(decision_source, str):
    print("false\x1f\x1f\x1f\x1f\x1f")
    sys.exit(0)

is_valid = required and decision_source == "repeated_reject_stagnation"
if status == "pending":
    is_valid = is_valid
elif status == "resolved":
    is_valid = is_valid and isinstance(resolution_action, str) and resolution_action in {"accept-as-is", "force-followup", "abort"}
else:
    is_valid = False

reason_out = reason if isinstance(reason, str) else ""
resolution_out = resolution_action if isinstance(resolution_action, str) else ""
print(
    "{}\x1f{}\x1f{}\x1f{}\x1f{}\x1f{}".format(
        "true" if is_valid else "false",
        "true" if required else "false",
        status,
        decision_source,
        reason_out,
        resolution_out,
    )
)
PY
}

is_supported_resolution_action() {
  local resolution_action="${1:-}"

  case "$resolution_action" in
    accept-as-is|force-followup|abort)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

escalation_artifact_is_valid() {
  local escalation_required="$1"
  local escalation_status="$2"
  local decision_source="$3"
  local resolution_action="$4"

  [[ "$escalation_required" == "true" ]] || return 1

  case "$escalation_status" in
    pending)
      [[ "$decision_source" == "repeated_reject_stagnation" ]] || return 1
      return 0
      ;;
    resolved)
      [[ "$decision_source" == "repeated_reject_stagnation" ]] || return 1
      is_supported_resolution_action "$resolution_action"
      return $?
      ;;
    *)
      return 1
      ;;
  esac
}


display_value() {
  local value="$1"
  if [[ -n "$value" ]]; then
    printf '%s\n' "$value"
  else
    printf 'unknown\n'
  fi
}

extract_merge_recommendation() {
  local review_file="$1"

  if recommendation="$(extract_strict_merge_recommendation "$review_file")"; then
    printf '%s\n' "$recommendation"
  else
    echo "invalid"
  fi
}

working_tree_is_clean() {
  local status_output

  if ! git -C "$ROOT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    return 0
  fi

  status_output="$(git -C "$ROOT_DIR" status --porcelain --untracked-files=normal -- . "$EPHEMERAL_LEDGER_EXCLUDE_PATHSPEC" 2>/dev/null || true)"
  [[ -z "$status_output" ]]
}

dirty_tree_reason() {
  printf '%s\n' "workspace-only changes detected; commit or discard them before review/classify/gate because those steps operate on committed HEAD only"
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

run_is_convergence_candidate() {
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

changed_files_match() {
  local left_run_dir="$1"
  local right_run_dir="$2"
  local left_sorted right_sorted

  left_sorted="$(mktemp)"
  right_sorted="$(mktemp)"

  sorted_effective_changed_files_for_run_to "$STORY_ID" "$left_run_dir" "$left_sorted" || {
    rm -f "$left_sorted" "$right_sorted"
    return 1
  }
  sorted_effective_changed_files_for_run_to "$STORY_ID" "$right_run_dir" "$right_sorted" || {
    rm -f "$left_sorted" "$right_sorted"
    return 1
  }

  if cmp -s "$left_sorted" "$right_sorted"; then
    rm -f "$left_sorted" "$right_sorted"
    return 0
  fi

  rm -f "$left_sorted" "$right_sorted"
  return 1
}

diff_patch_match() {
  local left_run_dir="$1"
  local right_run_dir="$2"
  local left_diff right_diff

  left_diff="$(mktemp)"
  right_diff="$(mktemp)"

  effective_diff_patch_for_run_to "$STORY_ID" "$left_run_dir" "$left_diff" || {
    rm -f "$left_diff" "$right_diff"
    return 1
  }
  effective_diff_patch_for_run_to "$STORY_ID" "$right_run_dir" "$right_diff" || {
    rm -f "$left_diff" "$right_diff"
    return 1
  }

  if cmp -s "$left_diff" "$right_diff"; then
    rm -f "$left_diff" "$right_diff"
    return 0
  fi

  rm -f "$left_diff" "$right_diff"
  return 1
}

review_surfaces_match() {
  local left_run_dir="$1"
  local right_run_dir="$2"

  changed_files_match "$left_run_dir" "$right_run_dir" || return 1
  if ! run_manifest_companion_filter_enabled "$left_run_dir" && ! run_manifest_companion_filter_enabled "$right_run_dir"; then
    return 0
  fi
  diff_patch_match "$left_run_dir" "$right_run_dir" || return 1
}

resolve_previous_run_dir() {
  local story_runs_root="$1"
  local target_run_dir="$2"
  local previous_run_dir=""
  local candidate_run_dir

  while IFS= read -r candidate_run_dir; do
    [[ "$candidate_run_dir" == "$target_run_dir" ]] && break
    previous_run_dir="$candidate_run_dir"
  done < <(list_story_run_dirs "$story_runs_root")

  [[ -n "$previous_run_dir" ]] || return 1
  printf '%s\n' "$previous_run_dir"
}

detect_non_converging_rerun_for_run() {
  local story_runs_root="$1"
  local run_dir="$2"
  local previous_run_dir previous_head latest_head

  previous_run_dir="$(resolve_previous_run_dir "$story_runs_root" "$run_dir" || true)"
  [[ -n "$previous_run_dir" ]] || return 1

  run_is_convergence_candidate "$previous_run_dir" || return 1
  run_is_convergence_candidate "$run_dir" || return 1

  previous_head="$(manifest_source_of_truth_head "$previous_run_dir/manifest.md")"
  latest_head="$(manifest_source_of_truth_head "$run_dir/manifest.md")"

  [[ "$previous_head" =~ ^[0-9a-f]{40}$ ]] || return 1
  [[ "$latest_head" =~ ^[0-9a-f]{40}$ ]] || return 1
  [[ "$previous_head" != "$latest_head" ]] || return 1

  review_surfaces_match \
    "$previous_run_dir" \
    "$run_dir" || return 1

  printf '%s\n' "$previous_run_dir"
}

run_has_gate_approved() {
  story_stage_loop_run_has_gate_approved "$1"
}

run_has_terminal_escalation_resolution() {
  story_stage_loop_run_has_terminal_escalation_resolution "$1"
}

run_participates_in_stage_loop() {
  story_stage_loop_run_participates "$1"
}

detect_same_head_stage_loop_cap_for_run() {
  story_stage_loop_detect_same_head_cap_for_run "$1" "$2" "$3"
}

classification_or_gate_reject_is_safety_driven() {
  local run_dir="$1"
  local classification_file="$run_dir/review_classification.md"
  local gate_file="$run_dir/review_gate_result.json"

  if [[ -f "$classification_file" ]]; then
    grep -Eiq 'MERGE BLOCKER|safety|source-of-truth|source of truth|security|stale|fidelity|regression|contract' "$classification_file" && return 0
  fi

  if [[ -f "$gate_file" ]]; then
    grep -Eiq 'MERGE BLOCKER|safety|source-of-truth|source of truth|security|stale|fidelity|regression|contract' "$gate_file" && return 0
  fi

  return 1
}

stage_loop_cap_requires_narrow_safety_fix() {
  local stage="$1"
  local run_dir="$2"

  case "$stage" in
    blocked_refresh_metadata_invalid|blocked_review_artifact_fidelity)
      return 0
      ;;
    blocked_classification_rejected|blocked_review_gate_rejected)
      classification_or_gate_reject_is_safety_driven "$run_dir"
      return $?
      ;;
    *)
      return 1
      ;;
  esac
}

strict_manual_finish_continuation_allowed() {
  local story_runs_root="$1"
  local run_dir="$2"
  local reviewed_head="$3"
  local checkout_head="$4"
  local previous_non_converging_run_dir parent_head

  [[ -n "$reviewed_head" ]] || return 1
  [[ -n "$checkout_head" ]] || return 1
  [[ "$reviewed_head" != "$checkout_head" ]] || return 1

  previous_non_converging_run_dir="$(detect_non_converging_rerun_for_run "$story_runs_root" "$run_dir" || true)"
  [[ -n "$previous_non_converging_run_dir" ]] || return 1

  parent_head="$(git -C "$ROOT_DIR" rev-parse --verify "${checkout_head}^" 2>/dev/null || true)"
  [[ -n "$parent_head" ]] || return 1

  [[ "$parent_head" == "$reviewed_head" ]]
}

resolve_review_head_contract() {
  local story_runs_root="$1"
  local run_dir="$2"
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

  if strict_manual_finish_continuation_allowed "$story_runs_root" "$run_dir" "$manifest_reviewed_head" "$checkout_head"; then
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

resolve_review_artifact_base() {
  local manifest_file="$1"
  local review_artifact_base

  review_artifact_base="$(manifest_value "$manifest_file" "review_artifact_base")"
  if [[ -z "$review_artifact_base" ]]; then
    return 1
  fi

  git -C "$ROOT_DIR" rev-parse --verify "${review_artifact_base}^{commit}" 2>/dev/null || return 1
}

run_can_recompute_review_surface() {
  local run_dir="$1"
  local manifest_file="$run_dir/manifest.md"
  local review_artifact_base run_head

  [[ -f "$manifest_file" ]] || return 1
  review_artifact_base="$(resolve_review_artifact_base "$manifest_file" || true)"
  run_head="$(manifest_source_of_truth_head "$manifest_file")"

  [[ "$review_artifact_base" =~ ^[0-9a-f]{40}$ ]] || return 1
  [[ "$run_head" =~ ^[0-9a-f]{40}$ ]]
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

sorted_effective_changed_files_for_run_to() {
  local story_id="$1"
  local run_dir="$2"
  local output_file="$3"
  local changed_files_file="$run_dir/changed_files.txt"
  local projection_state projection_status review_changed_files_file

  projection_state="$(read_semantic_projection_artifact_state "$run_dir")"
  IFS=$'\t' read -r projection_status _ <<< "$projection_state"
  if [[ "$projection_status" == "valid" ]]; then
    review_changed_files_file="$run_dir/review_changed_files.txt"
    [[ -f "$review_changed_files_file" ]] || return 1
    sorted_changed_files_to "$story_id" "$run_dir" "$review_changed_files_file" "$output_file"
    return 0
  fi
  if [[ "$projection_status" == "invalid" ]]; then
    return 1
  fi

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

read_semantic_projection_artifact_state() {
  local run_dir="$1"

  python3 - "$run_dir" <<'PY'
import hashlib
import json
import re
import sys
from pathlib import Path

run_dir = Path(sys.argv[1])
projection_path = run_dir / "semantic_projection.json"
manifest_path = run_dir / "manifest.md"
manifest_text = ""
manifest_expects_projection = False

if manifest_path.exists():
    manifest_text = manifest_path.read_text(encoding="utf-8")
    manifest_expects_projection = bool(
        re.search(r"^-\s+semantic_projection\.json\s*$", manifest_text, re.MULTILINE)
    )

if not projection_path.exists():
    if manifest_expects_projection:
        print(
            "invalid\tsemantic_projection_missing_expected\tsemantic projection artifact is required by the pinned run manifest but is missing"
        )
        sys.exit(0)
    print("missing\tsemantic_projection_missing\tprojection artifact not present")
    sys.exit(0)

if not manifest_path.exists():
    print("invalid\tsemantic_projection_manifest_missing\trequired file not found: manifest.md")
    sys.exit(0)

def no_dupes(pairs):
    data = {}
    for key, value in pairs:
        if key in data:
            raise ValueError(f"duplicate key: {key}")
        data[key] = value
    return data

def manifest_value(text: str, key: str) -> str:
    match = re.search(rf"^-\s+{re.escape(key)}:\s*(.*)$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""

try:
    payload = json.loads(projection_path.read_text(encoding="utf-8"), object_pairs_hook=no_dupes)
except Exception as exc:
    print(f"invalid\tsemantic_projection_invalid_json\tsemantic projection artifact is not valid JSON: {exc}")
    sys.exit(0)

if not isinstance(payload, dict):
    print("invalid\tsemantic_projection_invalid_payload\tsemantic projection artifact must contain a JSON object")
    sys.exit(0)

if payload.get("schema_version") != 1:
    print("invalid\tsemantic_projection_invalid_payload\tinvalid schema_version")
    sys.exit(0)
if payload.get("projection_kind") != "semantic_companion_filter":
    print("invalid\tsemantic_projection_invalid_payload\tinvalid projection_kind")
    sys.exit(0)
if payload.get("projection_source") != "run_stage":
    print("invalid\tsemantic_projection_invalid_payload\tinvalid projection_source")
    sys.exit(0)

manifest_head = manifest_value(manifest_text, "isolated_worktree_head") or manifest_value(manifest_text, "starting_head")

expected_manifest_values = {
    "story_id": manifest_value(manifest_text, "story_id"),
    "review_artifact_base": manifest_value(manifest_text, "review_artifact_base"),
    "source_of_truth_head": manifest_head,
    "execution_companion_filter_mode": manifest_value(manifest_text, "execution_companion_filter_mode"),
}

def heads_match(expected: str, actual: str) -> bool:
    if not expected or not actual:
        return False
    if expected == actual:
        return True
    return bool(re.fullmatch(r"[0-9a-f]{7,39}", expected) and actual.startswith(expected))

for key, expected_value in expected_manifest_values.items():
    if not expected_value:
        continue
    actual_value = payload.get(key)
    if key == "source_of_truth_head":
        if not isinstance(actual_value, str) or not heads_match(expected_value, actual_value):
            print(f"invalid\tsemantic_projection_manifest_mismatch\t{key} mismatch")
            sys.exit(0)
        continue
    if actual_value != expected_value:
        print(f"invalid\tsemantic_projection_manifest_mismatch\t{key} mismatch")
        sys.exit(0)

expected = {
    "changed_files": "changed_files.txt",
    "diff_patch": "diff.patch",
    "review_changed_files": "review_changed_files.txt",
}

artifacts = payload.get("artifacts")
if not isinstance(artifacts, dict):
    print("invalid\tsemantic_projection_artifacts_missing\tmissing artifacts block")
    sys.exit(0)

for key, expected_name in expected.items():
    entry = artifacts.get(key)
    if not isinstance(entry, dict):
        print(f"invalid\tsemantic_projection_missing_entry\tmissing artifact entry: {key}")
        sys.exit(0)
    if entry.get("path") != expected_name:
        print(f"invalid\tsemantic_projection_path_mismatch\t{key} path mismatch")
        sys.exit(0)
    sha = entry.get("sha256")
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha):
        print(f"invalid\tsemantic_projection_hash_invalid\tinvalid sha for {key}")
        sys.exit(0)

    artifact_path = run_dir / expected_name
    if not artifact_path.exists():
        print(f"invalid\tsemantic_projection_artifact_missing\tmissing file {expected_name}")
        sys.exit(0)

    actual_sha = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    if actual_sha != sha:
        print(f"invalid\tsemantic_projection_hash_mismatch\tsha mismatch for {expected_name}")
        sys.exit(0)

print("valid\tsemantic_projection_valid\tvalidated")
PY
}

effective_diff_patch_for_run_to() {
  local story_id="$1"
  local run_dir="$2"
  local output_file="$3"
  local diff_artifact="$run_dir/diff.patch"
  local projection_state projection_status

  projection_state="$(read_semantic_projection_artifact_state "$run_dir")"
  IFS=$'\t' read -r projection_status _ <<< "$projection_state"
  if [[ "$projection_status" == "valid" ]]; then
    [[ -f "$diff_artifact" ]] || return 1
    filter_review_fidelity_diff "$story_id" "$run_dir" < "$diff_artifact" > "$output_file"
    return 0
  fi
  if [[ "$projection_status" == "invalid" ]]; then
    return 1
  fi

  if run_manifest_companion_filter_enabled "$run_dir"; then
    recompute_filtered_diff_patch_for_run_to "$story_id" "$run_dir" "$output_file" || return 1
    return 0
  fi

  [[ -f "$diff_artifact" ]] || return 1
  filter_review_fidelity_diff "$story_id" "$run_dir" < "$diff_artifact" > "$output_file"
}

run_filtered_review_artifacts_match_recomputed_surface() {
  local run_dir="$1"
  local projection_state projection_status
  local manifest_file="$run_dir/manifest.md"
  local reviewed_head checkout_head
  local changed_files_artifact="$run_dir/changed_files.txt"
  local review_changed_files_artifact="$run_dir/review_changed_files.txt"
  local diff_artifact="$run_dir/diff.patch"
  local expected_changed_files normalized_changed_files expected_diff normalized_diff

  projection_state="$(read_semantic_projection_artifact_state "$run_dir")"
  IFS=$'\t' read -r projection_status _ <<< "$projection_state"
  if [[ "$projection_status" == "valid" ]]; then
    changed_files_artifact="$review_changed_files_artifact"
  fi
  if [[ "$projection_status" == "invalid" ]]; then
    return 1
  fi

  [[ -f "$changed_files_artifact" ]] || return 1
  [[ -f "$diff_artifact" ]] || return 1

  expected_changed_files="$(mktemp)"
  normalized_changed_files="$(mktemp)"
  expected_diff="$(mktemp)"
  normalized_diff="$(mktemp)"

  if ! recompute_filtered_changed_files_for_run_to "$STORY_ID" "$run_dir" "$expected_changed_files"; then
    rm -f "$expected_changed_files" "$normalized_changed_files" "$expected_diff" "$normalized_diff"
    return 1
  fi
  sorted_changed_files_to "$STORY_ID" "$run_dir" "$changed_files_artifact" "$normalized_changed_files"

  if ! recompute_filtered_diff_patch_for_run_to "$STORY_ID" "$run_dir" "$expected_diff"; then
    rm -f "$expected_changed_files" "$normalized_changed_files" "$expected_diff" "$normalized_diff"
    return 1
  fi
  filter_review_fidelity_diff "$STORY_ID" "$run_dir" < "$diff_artifact" > "$normalized_diff"

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

review_artifact_fidelity_status() {
  local run_dir="$1"
  local manifest_file="$2"
  local diff_artifact changed_files_artifact review_changed_files_artifact review_artifact_base reviewed_head checkout_head
  local changed_files_artifact_name
  local expected_diff_file expected_changed_files_file artifact_changed_files_file normalized_artifact_diff_file
  local projection_state projection_status projection_code projection_reason

  diff_artifact="$run_dir/diff.patch"
  changed_files_artifact="$run_dir/changed_files.txt"
  review_changed_files_artifact="$run_dir/review_changed_files.txt"

  projection_state="$(read_semantic_projection_artifact_state "$run_dir")"
  IFS=$'\t' read -r projection_status projection_code projection_reason <<< "$projection_state"
  if [[ "$projection_status" == "invalid" ]]; then
    printf 'reject\t%s\t%s\n' "$projection_code" "$projection_reason"
    return 0
  fi
  if [[ "$projection_status" == "valid" ]]; then
    changed_files_artifact="$review_changed_files_artifact"
  fi

  changed_files_artifact_name="$(basename "$changed_files_artifact")"

  if [[ ! -f "$diff_artifact" ]]; then
    printf 'reject\treview_diff_artifact_missing\trequired file not found: %s\n' "$diff_artifact"
    return 0
  fi

  if [[ ! -f "$changed_files_artifact" ]]; then
    printf 'reject\treview_changed_files_artifact_missing\trequired file not found: %s\n' "$changed_files_artifact"
    return 0
  fi

  if ! review_artifact_base="$(resolve_review_artifact_base "$manifest_file")"; then
    printf 'reject\treview_artifact_base_missing\trun manifest is missing or has invalid review_artifact_base; final-HEAD compliance is not proven for this manual-finish continuation\n'
    return 0
  fi

  expected_diff_file="$(mktemp)"
  expected_changed_files_file="$(mktemp)"
  artifact_changed_files_file="$(mktemp)"
  normalized_artifact_diff_file="$(mktemp)"

  if ! git -C "$ROOT_DIR" diff "$review_artifact_base" -- . "$EPHEMERAL_LEDGER_EXCLUDE_PATHSPEC" \
      | filter_review_fidelity_diff "$STORY_ID" "$run_dir" > "$expected_diff_file"; then
    rm -f "$expected_diff_file" "$expected_changed_files_file" "$artifact_changed_files_file" "$normalized_artifact_diff_file"
    printf 'reject\treview_diff_generation_failed\tunable to regenerate final-HEAD diff from review_artifact_base %s\n' "$review_artifact_base"
    return 0
  fi

  git -C "$ROOT_DIR" diff --name-only "$review_artifact_base" -- . "$EPHEMERAL_LEDGER_EXCLUDE_PATHSPEC" \
    | sed '/^$/d' \
    | filter_review_fidelity_paths "$STORY_ID" "$run_dir" "$expected_changed_files_file"

  if [[ $? -ne 0 ]]; then
    rm -f "$expected_diff_file" "$expected_changed_files_file" "$artifact_changed_files_file" "$normalized_artifact_diff_file"
    printf 'reject\treview_changed_files_generation_failed\tunable to regenerate final-HEAD changed_files from review_artifact_base %s\n' "$review_artifact_base"
    return 0
  fi

  if ! filter_review_fidelity_diff "$STORY_ID" "$run_dir" < "$diff_artifact" > "$normalized_artifact_diff_file"; then
    rm -f "$expected_diff_file" "$expected_changed_files_file" "$artifact_changed_files_file" "$normalized_artifact_diff_file"
    printf 'reject\treview_diff_artifact_invalid\treview artifact diff.patch could not be normalized; final-HEAD compliance is not proven for this manual-finish continuation\n'
    return 0
  fi

  sorted_changed_files_to "$STORY_ID" "$run_dir" "$changed_files_artifact" "$artifact_changed_files_file"

  if ! cmp -s "$artifact_changed_files_file" "$expected_changed_files_file"; then
    rm -f "$expected_diff_file" "$expected_changed_files_file" "$artifact_changed_files_file" "$normalized_artifact_diff_file"
    printf 'reject\treview_changed_files_mismatch\treview artifact %s does not prove final-HEAD compliance for this manual-finish continuation\n' "$changed_files_artifact_name"
    return 0
  fi

  if ! cmp -s "$normalized_artifact_diff_file" "$expected_diff_file"; then
    rm -f "$expected_diff_file" "$expected_changed_files_file" "$artifact_changed_files_file" "$normalized_artifact_diff_file"
    printf 'reject\treview_diff_patch_mismatch\treview artifact diff.patch does not prove final-HEAD compliance for this manual-finish continuation\n'
    return 0
  fi

  rm -f "$expected_diff_file" "$expected_changed_files_file" "$artifact_changed_files_file" "$normalized_artifact_diff_file"
  printf 'ok\treview_artifact_fidelity_valid\tartifact fidelity verified against final HEAD via review_artifact_base %s\n' "$review_artifact_base"
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

format_head_consistency_status() {
  local manifest_file="$1"
  local status expected_head current_head
  local head_contract_state head_contract_code effective_reviewed_head manifest_reviewed_head

  status="$(head_consistency_status "$manifest_file")"
  head_contract_state="$(resolve_review_head_contract "$STORY_RUNS_ROOT" "$RUN_DIR" "$manifest_file")"
  IFS=$'\x1f' read -r _ head_contract_code _ effective_reviewed_head manifest_reviewed_head _ <<< "$head_contract_state"
  if [[ "$head_contract_code" == "manual_finish_continuation_valid" ]]; then
    printf 'manual-finish continuation (manifest %s -> final reviewed HEAD %s)\n' \
      "$manifest_reviewed_head" \
      "$effective_reviewed_head"
    return 0
  fi
  case "$status" in
    match:*)
      printf 'match (%s)\n' "${status#match:}"
      ;;
    mismatch:*)
      expected_head="${status#mismatch:}"
      current_head="${expected_head#*:}"
      expected_head="${expected_head%%:*}"
      printf 'stale (manifest %s != checkout %s)\n' "$expected_head" "$current_head"
      ;;
    unknown:manifest_head_missing)
      printf 'unknown (manifest source-of-truth HEAD missing)\n'
      ;;
    unknown:current_head_unavailable:*)
      printf 'unknown (checkout HEAD unavailable; manifest %s)\n' "${status#unknown:current_head_unavailable:}"
      ;;
    *)
      printf 'unknown\n'
      ;;
  esac
}

review_prereq_status() {
  local run_dir="$1"
  local missing=()
  local artifact

  for artifact in \
    review_bundle.md \
    chatgpt_review_prompt.md \
    diff.patch \
    changed_files.txt \
    pytest.txt
  do
    if [[ ! -f "$run_dir/$artifact" ]]; then
      missing+=("$artifact")
    fi
  done

  if (( ${#missing[@]} == 0 )); then
    printf 'ready\n'
    return 0
  fi

  printf 'missing:%s\n' "$(IFS=,; printf '%s' "${missing[*]}")"
}

format_review_prereq_status() {
  local run_dir="$1"
  local prereq_status

  prereq_status="$(review_prereq_status "$run_dir")"
  case "$prereq_status" in
    ready)
      printf 'ready\n'
      ;;
    missing:*)
      printf 'missing (%s)\n' "${prereq_status#missing:}"
      ;;
    *)
      printf 'unknown\n'
      ;;
  esac
}

summarize_ai_review_status() {
  local run_dir="$1"
  local ai_review_file="$2"
  local raw_output_file="$3"
  local prereq_status validation_state validation_status validation_code validation_reason

  prereq_status="$(review_prereq_status "$run_dir")"
  validation_state="$(read_ai_review_artifact_state "$ai_review_file" "$raw_output_file" "$run_dir/chatgpt_review_prompt.md")"
  IFS=$'\t' read -r validation_status validation_code validation_reason <<< "$validation_state"

  if [[ -f "$ai_review_file" ]]; then
    if [[ "$validation_status" == "valid" ]]; then
      printf 'present\n'
    else
      printf 'present (invalid: %s)\n' "$validation_code"
    fi
    return 0
  fi

  if [[ "$prereq_status" != "ready" ]]; then
    printf 'missing (prerequisites %s)\n' "${prereq_status#missing:}"
    return 0
  fi

  if [[ "$validation_status" == "invalid" && "$validation_code" == "ai_review_normalization_failed" ]]; then
    printf 'failed normalization (raw output preserved)\n'
    return 0
  fi

  printf 'missing\n'
}

extract_pytest_summary() {
  local pytest_file="$1"
  [[ -f "$pytest_file" ]] || return 0

  python3 -c '
import sys
from pathlib import Path

path = Path(sys.argv[1])
lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

markers = ("passed", "failed", "error", "errors", "warning", "warnings", "skipped", "xfailed", "xpassed")
candidates = []

for line in lines:
    lower = line.lower()
    if any(marker in lower for marker in markers):
        candidates.append(line)

if candidates:
    print(candidates[-1])
elif lines:
    print(lines[-1])
' "$pytest_file"
}

summarize_changed_files() {
  local changed_files_file="$1"
  local count preview

  if [[ ! -f "$changed_files_file" ]]; then
    printf 'missing\n'
    return 0
  fi

  count="$(sed '/^[[:space:]]*$/d' "$changed_files_file" | wc -l | tr -d ' ')"
  if [[ "$count" == "0" ]]; then
    printf '0 files\n'
    return 0
  fi

  preview="$(
    sed '/^[[:space:]]*$/d' "$changed_files_file" \
      | head -n 3 \
      | awk 'BEGIN { sep="" } { printf "%s%s", sep, $0; sep=", " } END { printf "\n" }'
  )"
  if [[ "$count" -gt 3 ]]; then
    printf '%s files (%s, ...)\n' "$count" "$preview"
  else
    printf '%s files (%s)\n' "$count" "$preview"
  fi
}

summarize_pytest() {
  local manifest_file="$1"
  local pytest_file="$2"
  local pytest_exit_code pytest_summary

  pytest_exit_code="$(manifest_value "$manifest_file" "pytest_exit_code")"
  pytest_summary="$(extract_pytest_summary "$pytest_file")"

  if [[ -n "$pytest_exit_code" ]]; then
    case "$pytest_exit_code" in
      0) printf 'pass (exit 0';;
      *) printf 'fail (exit %s' "$pytest_exit_code";;
    esac
    if [[ -n "$pytest_summary" ]]; then
      printf '; %s)\n' "$pytest_summary"
    else
      printf '; output unavailable)\n'
    fi
    return 0
  fi

  if [[ -f "$pytest_file" ]]; then
    if [[ -n "$pytest_summary" ]]; then
      printf 'artifact present (%s)\n' "$pytest_summary"
    else
      printf 'artifact present (empty)\n'
    fi
  else
    printf 'missing\n'
  fi
}

summarize_review_pipeline() {
  local run_dir="$1"
  local ai_review_file="$2"
  local classification_file="$3"
  local gate_result_file="$4"
  local raw_output_file="$5"
  local escalation_file escalation_status escalation_required escalation_reason resolution_action escalation_valid escalation_state
  local prereq_status ai_status classification_status gate_status recommendation decision status source

  prereq_status="$(format_review_prereq_status "$run_dir")"
  ai_status="$(summarize_ai_review_status "$run_dir" "$ai_review_file" "$raw_output_file")"

  if [[ -f "$classification_file" ]]; then
    if recommendation="$(extract_merge_recommendation "$classification_file" 2>/dev/null)"; then
      classification_status="present ($recommendation)"
    else
      classification_status="present (invalid recommendation)"
    fi
  else
    classification_status="missing"
  fi

  if [[ -f "$gate_result_file" ]]; then
    decision="$(json_value "$gate_result_file" "decision")"
    status="$(json_value "$gate_result_file" "status")"
    source="$(json_value "$gate_result_file" "decision_source")"
    gate_status="present"
    if [[ -n "$decision" ]] || [[ -n "$status" ]] || [[ -n "$source" ]]; then
      gate_status="$gate_status (${decision:-unknown}"
      [[ -n "$status" ]] && gate_status="$gate_status/$status"
      [[ -n "$source" ]] && gate_status="$gate_status via $source"
      gate_status="$gate_status)"
    fi
  else
    gate_status="missing"
  fi

  escalation_file="$run_dir/escalation_result.json"
  if [[ -f "$escalation_file" ]]; then
    escalation_state="$(read_escalation_artifact_state "$escalation_file")"
    IFS=$'\x1f' read -r escalation_valid escalation_required escalation_status decision_source escalation_reason resolution_action <<<"$escalation_state"

    if [[ "$escalation_valid" == "true" ]] && escalation_artifact_is_valid "$escalation_required" "$escalation_status" "$decision_source" "$resolution_action"; then
      if [[ "$escalation_status" == "resolved" ]]; then
        printf 'Escalation: present (resolved via %s)\n' "${resolution_action:-unknown}"
      else
        printf 'Escalation: present (pending: %s)\n' "${escalation_reason:-unknown}"
      fi
    else
      printf 'Escalation: present (invalid)\n'
    fi
  else
    printf 'Escalation: missing\n'
  fi

  printf 'Review prerequisites: %s\n' "$prereq_status"
  printf 'AI review: %s\n' "$ai_status"
  printf 'Classification: %s\n' "$classification_status"
  printf 'Gate: %s\n' "$gate_status"
}

resume_next_command() {
  local script_name="$1"
  local story_id="$2"
  local run_dir="$3"

  printf 'AUTOMATION_RUN_DIR=%q automation/scripts/%s %q\n' "$run_dir" "$script_name" "$story_id"
}

run_story_command() {
  local story_id="$1"

  printf 'automation/scripts/run_story.sh %q\n' "$story_id"
}

print_operator_decision() {
  local story_id="$1"
  local run_dir="$2"
  local stage="$3"
  local latest_valid_stage="$4"
  local resume_safety="$5"
  local next_command="$6"
  local blocked_reason="$7"
  local manual_finish_continuation_allowed="$8"
  local loop_cap_status="${9:-false}"
  local loop_cap_decision="${10:-}"
  local loop_cap_runs="${11:-}"
  local current_state required_action allowed_actions forbidden_actions why

  current_state="Stage $stage (latest valid: $latest_valid_stage; resume safety: $resume_safety)"
  required_action="Re-run analyze with the same AUTOMATION_RUN_DIR after the blocker is resolved."
  allowed_actions="Use the pinned run only through AUTOMATION_RUN_DIR; re-run analyze after any manual state change."
  forbidden_actions="Passing RUN_DIR as a second positional argument; skipping committed-HEAD, dirty-tree, rerun, review, classify, or gate checks."
  why="${blocked_reason:-follow the pinned run state reported above}"

  case "$stage" in
    run_artifacts_ready)
      required_action="Run: $next_command"
      allowed_actions="AI review on the pinned run; re-run analyze afterward for a fresh decision."
      forbidden_actions="Re-running run_story without a new committed change; passing RUN_DIR as a second positional argument."
      why="Run artifacts are ready and review prerequisites are present."
      ;;
    ai_review_completed)
      required_action="Run: $next_command"
      allowed_actions="Classification on the pinned run; re-run analyze afterward for a fresh decision."
      forbidden_actions="Running the gate before classification; passing RUN_DIR as a second positional argument."
      why="AI review is present and valid, and no valid classification exists yet."
      ;;
    classification_approved)
      required_action="Run: $next_command"
      allowed_actions="Review gate on the pinned run; re-run analyze afterward for a fresh decision."
      forbidden_actions="Editing files before gate; re-running run_story without a new committed change; passing RUN_DIR as a second positional argument."
      why="Classification is approve, prerequisites are ready, and the committed-HEAD review path is available."
      ;;
    review_gate_passed)
      required_action="Proceed to merge review on the current committed HEAD. Story closure still requires PR merge, branch cleanup, local main update, and registry check."
      allowed_actions="Merge review on the clean committed HEAD; re-run analyze if you need to confirm the same pinned run again."
      forbidden_actions="Marking the story closed before PR merge, cleanup, main update, and registry closeout; passing RUN_DIR as a second positional argument."
      why="The review gate passed and analyze did not find a remaining evidence or dirty-tree blocker."
      ;;
    blocked_dirty_working_tree)
      required_action="Commit or discard workspace-only changes, then re-run analyze with the same AUTOMATION_RUN_DIR."
      allowed_actions="Cleaning the working tree; re-running analyze once committed HEAD is clean again."
      forbidden_actions="Review, AI review, classification, gate, or merge review while the tree is dirty; re-running run_story for this blocker."
      why="${blocked_reason:-dirty workspace-only changes block committed-HEAD review actions}"
      ;;
    blocked_non_converging_rerun)
      required_action="Finish the story manually in the workspace, commit the result, then re-run analyze. Do not rerun run_story first."
      allowed_actions="Manual finish work; committing the manual finish; re-running analyze on the same pinned run."
      forbidden_actions="Another run_story rerun; review/classify/gate before the manual finish is committed."
      why="${blocked_reason:-a committed-head rerun repeated the prior review surface, so manual finish is the only safe continuation}"
      ;;
    blocked_stage_loop_cap_safety)
      required_action="Stop blind continuation. Fix only the explicit safety/source-of-truth blocker, commit the narrow fix, then re-run analyze."
      allowed_actions="One narrow safety/source-of-truth fix; re-running analyze; using no-Codex refresh only if implementation is already accepted, the tree is clean, and only review evidence must be refreshed."
      forbidden_actions="Another blind run_story rerun; another blind refresh; non-safety polish; broad refactor; bypassing committed-HEAD review contracts."
      why="${blocked_reason:-the same reviewed HEAD has churned through repeated pinned runs and only a narrow safety/source-of-truth fix is still allowed}"
      ;;
    blocked_stage_loop_cap_escalation)
      required_action="Stop automatic continuation and make an explicit operator decision: narrow safety fix only if proven, otherwise follow-up, escalation, or abort."
      allowed_actions="Escalation for repeated evidence/fidelity churn; follow-up for non-safety polish or broad refactor; operator override only where existing policy explicitly allows it."
      forbidden_actions="Another blind run_story rerun; another blind refresh; treating classification/gate reject as cleared without an explicit decision."
      why="${blocked_reason:-the same reviewed HEAD has repeated non-converging review churn and must be resolved explicitly instead of by another blind continuation}"
      ;;
    blocked_manual_finish_final_head_unproven)
      required_action="Update the pinned review artifacts so they prove final-HEAD compliance for the committed manual-finish continuation, then re-run analyze."
      allowed_actions="Refreshing pinned review artifacts for the committed manual-finish HEAD; re-running analyze afterward."
      forbidden_actions="Another run_story rerun; continuing review/gate before final-HEAD compliance is proven."
      why="${blocked_reason:-manual-finish continuation is allowed, but the pinned artifacts do not yet prove final-HEAD compliance}"
      ;;
    manual_finish_ready_for_review)
      required_action="Run: $next_command"
      allowed_actions="Continue review from the committed manual-finish HEAD with the pinned run; re-run analyze after each review-stage step."
      forbidden_actions="Another run_story rerun; restarting from the old pre-manual-finish path; passing RUN_DIR as a second positional argument."
      why="Manual finish is committed and analyze validated the exact continuation path."
      ;;
    blocked_stale_run_evidence)
      required_action="Re-run run_story from the current committed HEAD, then analyze the new run with AUTOMATION_RUN_DIR."
      allowed_actions="A fresh committed-HEAD rerun; re-running analyze on the new pinned run."
      forbidden_actions="Review, classify, gate, or merge review using stale run artifacts."
      why="${blocked_reason:-the pinned run manifest HEAD no longer matches the current checkout HEAD}"
      ;;
    blocked_refresh_metadata_invalid)
      required_action="Re-run automation/scripts/refresh_review_evidence.sh $story_id from a clean non-main branch, then analyze the new pinned run."
      allowed_actions="Refreshing no-Codex review evidence for the current committed HEAD."
      forbidden_actions="Review, AI review, classification, gate, or merge review using refresh evidence with missing or invalid metadata."
      why="${blocked_reason:-refresh evidence metadata is invalid}"
      ;;
    blocked_codex_failed|blocked_materialization_failed|blocked_pytest_failed|blocked_no_changed_files|blocked_review_prerequisites_missing)
      required_action="Run: $(run_story_command "$story_id")"
      allowed_actions="A fresh run_story from committed HEAD; re-running analyze on the new pinned run."
      forbidden_actions="Proceeding to review-stage from incomplete or invalid run artifacts."
      why="${blocked_reason:-the current run artifacts are incomplete or invalid for review-stage}"
      ;;
    blocked_review_artifact_fidelity)
      required_action="Do not continue review-stage from this pinned run. Re-run run_story from the current committed HEAD, then analyze the new run with AUTOMATION_RUN_DIR."
      allowed_actions="A fresh committed-HEAD run_story; re-running analyze on the new pinned run."
      forbidden_actions="AI review, classification, gate, or merge review using this fidelity-blocked pinned run; passing RUN_DIR as a second positional argument."
      why="${blocked_reason:-filtered review artifacts are stale or inconsistent with recomputed baseline}"
      ;;
    blocked_ai_review_normalization_failed|blocked_ai_review_invalid|blocked_classification_invalid)
      required_action="Run: $next_command"
      allowed_actions="Regenerating the current review-stage artifact on the pinned run; re-running analyze afterward."
      forbidden_actions="Skipping to a later review-stage command while the current artifact is invalid."
      why="${blocked_reason:-the current pinned review-stage artifact is invalid and must be regenerated}"
      ;;
    blocked_classification_rejected)
      required_action="Inspect the review findings and decide whether to fix the implementation and rerun, or handle the reject through the existing escalation workflow."
      allowed_actions="Reviewing findings; a follow-up implementation rerun if fixes are needed; escalation if the reject must be resolved explicitly."
      forbidden_actions="Running the gate or merge review as if classification approved."
      why="${blocked_reason:-classification returned reject}"
      ;;
    blocked_review_gate_rejected)
      required_action="Inspect gate/classification findings and resolve them before any merge review."
      allowed_actions="Applying fixes and rerunning from committed HEAD; using the existing escalation path if required by the gate outcome."
      forbidden_actions="Merge review or story closure from a rejected gate result."
      why="${blocked_reason:-the review gate did not approve this pinned run}"
      ;;
    blocked_escalation_required)
      required_action="Resolve the escalation first: $next_command"
      allowed_actions="A single explicit escalation resolution for the pinned run."
      forbidden_actions="Continuing normal review-stage commands before the escalation is resolved."
      why="${blocked_reason:-repeated reject stagnation requires an explicit operator resolution}"
      ;;
    escalation_force_followup_resolved)
      required_action="Run: $next_command"
      allowed_actions="Starting the required follow-up implementation run."
      forbidden_actions="Treating the current rejected run as approved."
      why="Escalation was resolved as force-followup."
      ;;
    escalation_accepted_as_is|escalation_aborted)
      required_action="No further automation step is allowed from this pinned run."
      allowed_actions="Stop and handle the story according to the recorded escalation resolution."
      forbidden_actions="Continuing review-stage automation from this run as if it were approved."
      why="${blocked_reason:-the escalation resolution made this run terminal}"
      ;;
    blocked_manifest_head_missing|blocked_checkout_head_unavailable)
      required_action="Restore committed-HEAD evidence verification, then re-run analyze before any review-stage action."
      allowed_actions="Repairing the repository/checkout state; re-running analyze once HEAD can be verified again."
      forbidden_actions="Review, classify, gate, or merge review without verified committed-HEAD evidence."
      why="${blocked_reason:-analyze cannot verify the run against the current checkout HEAD}"
      ;;
  esac

  if [[ "$manual_finish_continuation_allowed" == "true" && "$stage" != "manual_finish_ready_for_review" && "$stage" != "blocked_manual_finish_final_head_unproven" && "$stage" != "review_gate_passed" ]]; then
    forbidden_actions="$forbidden_actions Another run_story rerun before the manual-finish continuation is completed."
  fi

  printf 'OPERATOR DECISION:\n'
  printf 'Current state: %s\n' "$current_state"
  printf 'Required next action: %s\n' "$required_action"
  printf 'Allowed actions: %s\n' "$allowed_actions"
  printf 'Forbidden actions: %s\n' "$forbidden_actions"
  printf 'Why: %s\n' "$why"
  if [[ "$loop_cap_status" == "true" ]]; then
    printf 'LOOP CAP: REACHED\n'
    printf 'REQUIRED DECISION: %s\n' "$loop_cap_decision"
    if [[ -n "$loop_cap_runs" ]]; then
      printf 'Loop cap runs: %s\n' "$loop_cap_runs"
    fi
  fi
}

print_stage_gate_guidance() {
  local stage="$1"
  local latest_valid_stage="$2"
  local manual_finish_continuation_allowed="$3"

  case "$stage" in
    blocked_dirty_working_tree)
      printf 'Review-stage: blocked; commit or discard workspace-only changes first because review/classify/gate operate on committed HEAD only\n'
      printf 'Rerun gate: wait; review-stage stays blocked until commit/discard restores a clean committed HEAD\n'
      return 0
      ;;
    blocked_non_converging_rerun)
      printf 'Review-stage: blocked; manual finish must be committed before review-stage is allowed again\n'
      printf 'Rerun gate: forbidden; manual-finish continuation is active until manual finish is complete\n'
      return 0
      ;;
    blocked_stage_loop_cap_safety)
      printf 'Review-stage: blocked; only a narrow safety/source-of-truth fix may continue this loop-capped path\n'
      printf 'Rerun gate: forbidden; do not blind-rerun run_story or refresh until the explicit blocker is fixed and recommitted\n'
      return 0
      ;;
    blocked_stage_loop_cap_escalation)
      printf 'Review-stage: blocked; repeated stage churn requires an explicit operator decision before any further continuation\n'
      printf 'Rerun gate: forbidden; do not blind-rerun run_story or refresh from this loop-capped state\n'
      return 0
      ;;
    blocked_manual_finish_final_head_unproven)
      printf 'Review-stage: blocked; prove final-HEAD compliance for the committed manual-finish continuation before review-stage is allowed\n'
      printf 'Rerun gate: forbidden; manual-finish continuation must proceed from committed HEAD without another rerun\n'
      return 0
      ;;
    manual_finish_ready_for_review)
      printf 'Review-stage: allowed on the committed manual-finish HEAD; the manual-finish continuation is the active review path\n'
      printf 'Rerun gate: forbidden; continue review from the committed manual-finish HEAD without another rerun\n'
      return 0
      ;;
  esac

  case "$latest_valid_stage" in
    run_artifacts_ready|ai_review_completed|classification_approved|review_gate_passed)
      if [[ "$manual_finish_continuation_allowed" == "true" ]]; then
        printf 'Review-stage: allowed on the committed manual-finish HEAD; the manual-finish continuation is the active review path\n'
        printf 'Rerun gate: forbidden; continue review from the committed manual-finish HEAD without another rerun\n'
      else
        printf 'Review-stage: allowed; this committed-head rerun completed the required review sequence for the pinned run\n'
        printf 'Rerun gate: no additional run_story rerun is needed before review/classify/gate on committed HEAD\n'
      fi
      ;;
  esac
}

summarize_workflow_resume() {
  local story_id="$1"
  local run_dir="$2"
  local manifest_file="$3"
  local changed_files_file="$4"
  local pytest_file="$5"
  local ai_review_file="$6"
  local classification_file="$7"
  local gate_result_file="$8"
  local raw_output_file="$9"
  local escalation_file
  local gate_decision gate_status recommendation pytest_exit_code codex_exit_code materialization_status changed_files_count changed_files_detected prereq_status
  local escalation_status escalation_required escalation_reason resolution_action escalation_decision_source escalation_valid escalation_state
  local head_status expected_head current_head stage latest_valid_stage resume_safety blocked_reason next_command decision_source
  local ai_review_validation_state ai_review_validation_status ai_review_validation_code ai_review_validation_reason
  local previous_non_converging_run_dir reviewed_head checkout_head manual_finish_continuation_allowed
  local head_contract_state head_contract_code final_head_fidelity_state final_head_fidelity_status final_head_fidelity_code final_head_fidelity_reason
  local filtered_review_surface_status filtered_review_surface_code filtered_review_surface_reason
  local projection_state projection_status projection_code projection_reason
  local refresh_metadata_state refresh_metadata_status refresh_metadata_code refresh_metadata_reason
  local loop_cap_state loop_cap_count loop_cap_head loop_cap_runs loop_cap_status loop_cap_decision

  gate_decision="$(json_value "$gate_result_file" "decision")"
  gate_status="$(json_value "$gate_result_file" "status")"
  decision_source="$(json_value "$gate_result_file" "decision_source")"
  recommendation="$(extract_merge_recommendation "$classification_file" 2>/dev/null || true)"
  pytest_exit_code="$(manifest_value "$manifest_file" "pytest_exit_code")"
  changed_files_detected="$(manifest_value "$manifest_file" "changed_files_detected")"
  codex_exit_code="$(manifest_value "$manifest_file" "codex_exit_code")"
  materialization_status="$(manifest_value "$manifest_file" "materialization_status")"
  prereq_status="$(review_prereq_status "$run_dir")"
  head_status="$(head_consistency_status "$manifest_file")"
  ai_review_validation_state="$(read_ai_review_artifact_state "$ai_review_file" "$raw_output_file" "$run_dir/chatgpt_review_prompt.md" 2>/dev/null || true)"
  IFS=$'\t' read -r ai_review_validation_status ai_review_validation_code ai_review_validation_reason <<<"$ai_review_validation_state"
  escalation_file="$run_dir/escalation_result.json"
  escalation_state="$(read_escalation_artifact_state "$escalation_file")"
  IFS=$'\x1f' read -r escalation_valid escalation_required escalation_status escalation_decision_source escalation_reason resolution_action <<<"$escalation_state"
  previous_non_converging_run_dir="$(detect_non_converging_rerun_for_run "$STORY_RUNS_ROOT" "$run_dir" || true)"
  reviewed_head="$(manifest_source_of_truth_head "$manifest_file")"
  checkout_head="$(current_checkout_head)"
  manual_finish_continuation_allowed="false"
  head_contract_state="$(resolve_review_head_contract "$STORY_RUNS_ROOT" "$run_dir" "$manifest_file")"
  IFS=$'\x1f' read -r _ head_contract_code _ _ _ _ <<<"$head_contract_state"
  if [[ "$head_contract_code" == "manual_finish_continuation_valid" ]]; then
    manual_finish_continuation_allowed="true"
    final_head_fidelity_state="$(review_artifact_fidelity_status "$run_dir" "$manifest_file")"
    IFS=$'\t' read -r final_head_fidelity_status final_head_fidelity_code final_head_fidelity_reason <<<"$final_head_fidelity_state"
  else
    final_head_fidelity_status=""
    final_head_fidelity_code=""
    final_head_fidelity_reason=""
  fi
  filtered_review_surface_status="valid"
  filtered_review_surface_code=""
  filtered_review_surface_reason=""
  projection_state="$(read_semantic_projection_artifact_state "$run_dir")"
  IFS=$'\t' read -r projection_status projection_code projection_reason <<<"$projection_state"
  refresh_metadata_state="$(read_refresh_evidence_metadata_state "$run_dir" "$STORY_ID")"
  IFS=$'\t' read -r refresh_metadata_status refresh_metadata_code refresh_metadata_reason <<<"$refresh_metadata_state"
  if [[ "$projection_status" == "invalid" ]]; then
    filtered_review_surface_status="invalid"
    filtered_review_surface_code="$projection_code"
    filtered_review_surface_reason="$projection_reason"
  elif [[ "$manual_finish_continuation_allowed" != "true" && "$prereq_status" == "ready" ]] \
    && { [[ "$projection_status" == "valid" ]] || run_manifest_companion_filter_enabled "$run_dir"; }; then
    if ! run_filtered_review_artifacts_match_recomputed_surface "$run_dir"; then
      filtered_review_surface_status="invalid"
      filtered_review_surface_code="review_surface_mismatch"
      filtered_review_surface_reason="filtered review artifacts are stale or inconsistent with recomputed baseline"
    fi
  fi

  if [[ -f "$changed_files_file" ]]; then
    changed_files_count="$(sed '/^[[:space:]]*$/d' "$changed_files_file" | wc -l | tr -d ' ')"
  else
    changed_files_count=""
  fi

  stage="run_artifacts_pending"
  latest_valid_stage="none"
  resume_safety="safe"
  blocked_reason=""
  next_command="$(run_story_command "$story_id")"

  if [[ "$head_status" == mismatch:* && "$manual_finish_continuation_allowed" != "true" ]]; then
    expected_head="${head_status#mismatch:}"
    current_head="${expected_head#*:}"
    expected_head="${expected_head%%:*}"
    stage="blocked_stale_run_evidence"
    latest_valid_stage="none"
    resume_safety="blocked"
    blocked_reason="manifest HEAD $expected_head does not match checkout HEAD $current_head"
    next_command="none"
  elif [[ "$refresh_metadata_status" == "invalid" ]]; then
    stage="blocked_refresh_metadata_invalid"
    latest_valid_stage="none"
    resume_safety="blocked"
    blocked_reason="${refresh_metadata_reason:-refresh metadata invalid} ($refresh_metadata_code)"
    next_command="none"
  elif [[ -n "$codex_exit_code" && "$codex_exit_code" != "0" ]]; then
    stage="blocked_codex_failed"
    latest_valid_stage="none"
    resume_safety="blocked"
    blocked_reason="Codex execution failed (codex_exit_code=$codex_exit_code)"
    next_command="automation/scripts/run_story.sh $story_id"
  elif [[ -n "$materialization_status" && "$materialization_status" != "applied" && "$materialization_status" != "not_needed" ]]; then
    stage="blocked_materialization_failed"
    latest_valid_stage="none"
    resume_safety="blocked"
    blocked_reason="materialization_status=$materialization_status"
    next_command="automation/scripts/run_story.sh $story_id"
  elif [[ -n "$pytest_exit_code" && "$pytest_exit_code" != "0" ]]; then
    stage="blocked_pytest_failed"
    latest_valid_stage="none"
    resume_safety="blocked"
    blocked_reason="pytest failed (pytest_exit_code=$pytest_exit_code)"
    next_command="automation/scripts/run_story.sh $story_id"
  elif [[ "$changed_files_detected" == "no" || "$changed_files_count" == "0" ]]; then
    stage="blocked_no_changed_files"
    latest_valid_stage="none"
    resume_safety="blocked"
    blocked_reason="run reported no changed files"
    next_command="automation/scripts/run_story.sh $story_id"
  elif [[ "$prereq_status" != "ready" ]]; then
    stage="blocked_review_prerequisites_missing"
    latest_valid_stage="none"
    resume_safety="blocked"
    blocked_reason="missing review prerequisites: ${prereq_status#missing:}"
    next_command="automation/scripts/run_story.sh $story_id"
  elif [[ "$filtered_review_surface_status" == "invalid" ]]; then
    stage="blocked_review_artifact_fidelity"
    latest_valid_stage="run_artifacts_ready"
    resume_safety="blocked"
    blocked_reason="${filtered_review_surface_reason:-filtered review artifacts are stale or inconsistent with recomputed baseline}"
    next_command="automation/scripts/run_story.sh $story_id"
  elif [[ -n "$previous_non_converging_run_dir" && "$manual_finish_continuation_allowed" != "true" ]]; then
    stage="blocked_non_converging_rerun"
    latest_valid_stage="run_artifacts_ready"
    resume_safety="blocked"
    blocked_reason="latest committed-head rerun matched changed_files.txt from previous run $(basename "$previous_non_converging_run_dir"); manual finish required"
    next_command="none"
  elif [[ "$manual_finish_continuation_allowed" == "true" && "$final_head_fidelity_status" == "reject" ]]; then
    stage="blocked_manual_finish_final_head_unproven"
    latest_valid_stage="run_artifacts_ready"
    resume_safety="blocked"
    blocked_reason="$final_head_fidelity_reason ($final_head_fidelity_code)"
    next_command="none"
  else
    stage="run_artifacts_ready"
    latest_valid_stage="run_artifacts_ready"
    next_command="$(resume_next_command "ai_review_story_run.sh" "$story_id" "$run_dir")"
    if [[ "$manual_finish_continuation_allowed" == "true" ]]; then
      stage="manual_finish_ready_for_review"
      latest_valid_stage="manual_finish_ready_for_review"
    fi

    if [[ "$ai_review_validation_status" == "invalid" && "$ai_review_validation_code" == "ai_review_normalization_failed" ]]; then
      stage="blocked_ai_review_normalization_failed"
      blocked_reason="AI review normalization failed; inspect ai_review_raw_output.txt"
      next_command="$(resume_next_command "ai_review_story_run.sh" "$story_id" "$run_dir")"
    elif [[ -f "$ai_review_file" ]]; then
      if [[ "$ai_review_validation_status" != "valid" ]]; then
        stage="blocked_ai_review_invalid"
        blocked_reason="invalid AI review artifact (${ai_review_validation_code:-unknown})"
        next_command="$(resume_next_command "ai_review_story_run.sh" "$story_id" "$run_dir")"
      else
        stage="ai_review_completed"
        latest_valid_stage="ai_review_completed"
        next_command="$(resume_next_command "classify_review_story_run.sh" "$story_id" "$run_dir")"

        if [[ "$recommendation" == "approve" ]]; then
          stage="classification_approved"
          latest_valid_stage="classification_approved"
          next_command="$(resume_next_command "review_gate_story_run.sh" "$story_id" "$run_dir")"
        elif [[ "$recommendation" == "reject" ]]; then
          stage="blocked_classification_rejected"
          latest_valid_stage="ai_review_completed"
          resume_safety="blocked"
          blocked_reason="classification merge recommendation is reject"
          next_command="none"
        elif [[ -f "$classification_file" ]]; then
          stage="blocked_classification_invalid"
          latest_valid_stage="ai_review_completed"
          next_command="$(resume_next_command "classify_review_story_run.sh" "$story_id" "$run_dir")"
        fi
      fi
    fi
  fi

  if [[ -f "$gate_result_file" ]]; then
    if [[ "$gate_decision" == "approve" && "$gate_status" == "passed" ]]; then
      stage="review_gate_passed"
      latest_valid_stage="review_gate_passed"
      next_command="none"
      if [[ "$head_status" == "unknown:manifest_head_missing" ]]; then
        stage="blocked_manifest_head_missing"
        resume_safety="blocked"
        blocked_reason="manifest source-of-truth HEAD missing"
      elif [[ "$head_status" == unknown:current_head_unavailable:* ]]; then
        stage="blocked_checkout_head_unavailable"
        resume_safety="blocked"
        blocked_reason="checkout HEAD unavailable for evidence verification"
      elif working_tree_is_clean; then
        resume_safety="safe"
        blocked_reason=""
      else
        stage="blocked_dirty_working_tree"
        resume_safety="blocked"
        blocked_reason="$(dirty_tree_reason)"
      fi
    else
      if [[ -f "$escalation_file" ]] && ([[ "$escalation_valid" != "true" ]] || ! escalation_artifact_is_valid "$escalation_required" "$escalation_status" "$escalation_decision_source" "$resolution_action"); then
        stage="blocked_invalid_escalation_artifact"
        latest_valid_stage="ai_review_completed"
        resume_safety="blocked"
        blocked_reason="escalation artifact is invalid"
        next_command="none"
      elif [[ "$escalation_required" == "true" && "$escalation_status" != "resolved" ]]; then
        stage="blocked_escalation_required"
        latest_valid_stage="ai_review_completed"
        resume_safety="blocked"
        blocked_reason="${escalation_reason:-repeated reject stagnation}"
        next_command="$(resume_next_command "escalate_story.sh" "$story_id" "$run_dir") <accept-as-is|force-followup|abort>"
      elif [[ "$escalation_required" == "true" && "$escalation_status" == "resolved" && "$resolution_action" == "force-followup" ]]; then
        stage="escalation_force_followup_resolved"
        latest_valid_stage="ai_review_completed"
        resume_safety="safe"
        blocked_reason=""
        next_command="$(run_story_command "$story_id")"
      elif [[ "$escalation_required" == "true" && "$escalation_status" == "resolved" && "$resolution_action" == "accept-as-is" ]]; then
        stage="escalation_accepted_as_is"
        latest_valid_stage="ai_review_completed"
        resume_safety="blocked"
        blocked_reason="operator resolved escalation as accept-as-is"
        next_command="none"
      elif [[ "$escalation_required" == "true" && "$escalation_status" == "resolved" && "$resolution_action" == "abort" ]]; then
        stage="escalation_aborted"
        latest_valid_stage="ai_review_completed"
        resume_safety="blocked"
        blocked_reason="operator aborted the story after escalation"
        next_command="none"
      else
        stage="blocked_review_gate_rejected"
        if [[ "$recommendation" == "approve" ]]; then
          latest_valid_stage="classification_approved"
        elif [[ -f "$ai_review_file" ]]; then
          latest_valid_stage="ai_review_completed"
        else
          latest_valid_stage="run_artifacts_ready"
        fi
        resume_safety="blocked"
        blocked_reason="gate decision ${gate_decision:-unknown}/${gate_status:-unknown}${decision_source:+ via $decision_source}"
        next_command="none"
      fi
    fi
  elif [[ "$stage" == "classification_approved" ]]; then
    if [[ "$head_status" == "unknown:manifest_head_missing" ]]; then
      stage="blocked_manifest_head_missing"
      resume_safety="blocked"
      blocked_reason="manifest source-of-truth HEAD missing"
      next_command="none"
    elif [[ "$head_status" == unknown:current_head_unavailable:* ]]; then
      stage="blocked_checkout_head_unavailable"
      resume_safety="blocked"
      blocked_reason="checkout HEAD unavailable for evidence verification"
      next_command="none"
    elif working_tree_is_clean; then
      resume_safety="safe"
    else
      stage="blocked_dirty_working_tree"
      resume_safety="blocked"
      blocked_reason="$(dirty_tree_reason)"
      next_command="none"
    fi
  elif [[ "$stage" == "ai_review_completed" ]]; then
    if [[ "$head_status" == "unknown:manifest_head_missing" ]]; then
      stage="blocked_manifest_head_missing"
      resume_safety="blocked"
      blocked_reason="manifest source-of-truth HEAD missing"
      next_command="none"
    elif [[ "$head_status" == unknown:current_head_unavailable:* ]]; then
      stage="blocked_checkout_head_unavailable"
      resume_safety="blocked"
      blocked_reason="checkout HEAD unavailable for evidence verification"
      next_command="none"
    elif working_tree_is_clean; then
      resume_safety="safe"
    else
      stage="blocked_dirty_working_tree"
      resume_safety="blocked"
      blocked_reason="$(dirty_tree_reason)"
      next_command="none"
    fi
  fi

  loop_cap_status="false"
  loop_cap_decision=""
  loop_cap_runs=""
  if [[ "$stage" == "blocked_non_converging_rerun" ]]; then
    loop_cap_status="true"
    loop_cap_decision="manual_finish"
    loop_cap_runs="$(basename "$previous_non_converging_run_dir") $(basename "$run_dir")"
  fi
  if loop_cap_state="$(detect_same_head_stage_loop_cap_for_run "$STORY_RUNS_ROOT" "$run_dir" "$stage" || true)" && [[ -n "$loop_cap_state" ]]; then
    IFS=$'\x1f' read -r loop_cap_count loop_cap_head loop_cap_runs <<<"$loop_cap_state"
    loop_cap_status="true"
    next_command="none"
    resume_safety="blocked"
    if stage_loop_cap_requires_narrow_safety_fix "$stage" "$run_dir"; then
      stage="blocked_stage_loop_cap_safety"
      latest_valid_stage="run_artifacts_ready"
      loop_cap_decision="narrow_safety_fix"
      blocked_reason="stage-loop cap reached after $loop_cap_count same-HEAD pinned runs for reviewed HEAD $loop_cap_head; fix only the explicit safety/source-of-truth blocker before continuing"
    else
      stage="blocked_stage_loop_cap_escalation"
      if [[ "$latest_valid_stage" == "none" ]]; then
        latest_valid_stage="run_artifacts_ready"
      fi
      loop_cap_decision="operator_escalation"
      blocked_reason="stage-loop cap reached after $loop_cap_count same-HEAD pinned runs for reviewed HEAD $loop_cap_head; repeated refresh/review/classify churn must resolve through explicit escalation or follow-up"
    fi
  fi

  printf 'Current stage: %s\n' "$stage"
  printf 'Latest valid stage: %s\n' "$latest_valid_stage"
  printf 'Resume safety: %s\n' "$resume_safety"
  printf 'Next recommended command: %s\n' "$next_command"
  if [[ -n "$blocked_reason" ]]; then
    printf 'Blocked reason: %s\n' "$blocked_reason"
  fi
  if [[ "$refresh_metadata_status" == "valid" ]]; then
    printf 'Refresh evidence: valid (no-Codex refresh metadata verified)\n'
  elif [[ "$refresh_metadata_status" == "invalid" ]]; then
    printf 'Refresh evidence: invalid (%s)\n' "$refresh_metadata_code"
  fi
  print_stage_gate_guidance "$stage" "$latest_valid_stage" "$manual_finish_continuation_allowed"
  print_operator_decision \
    "$story_id" \
    "$run_dir" \
    "$stage" \
    "$latest_valid_stage" \
    "$resume_safety" \
    "$next_command" \
    "$blocked_reason" \
    "$manual_finish_continuation_allowed" \
    "$loop_cap_status" \
    "$loop_cap_decision" \
    "$loop_cap_runs"
  if [[ "$stage" == "blocked_non_converging_rerun" ]]; then
    printf 'Manual finish: inspect workspace-only changes, finish the story manually, commit the result to HEAD, then continue review on committed HEAD without rerunning automation/scripts/run_story.sh\n'
  elif [[ "$stage" == "blocked_manual_finish_final_head_unproven" ]]; then
    printf 'Manual finish evidence pending: update the pinned review artifacts so they prove final-HEAD compliance for the committed manual-finish continuation before continuing review\n'
  elif [[ "$stage" == "manual_finish_ready_for_review" ]]; then
    printf 'Manual finish complete: committed HEAD moved past the run manifest after a non-converging rerun; continue review on the committed HEAD using the pinned run artifacts\n'
  elif [[ "$stage" == "blocked_stage_loop_cap_safety" ]]; then
    printf 'Loop cap guidance: one narrow safety/source-of-truth fix is allowed; after commit, use no-Codex refresh only if implementation is already accepted and only review evidence needs refresh\n'
  elif [[ "$stage" == "blocked_stage_loop_cap_escalation" ]]; then
    printf 'Loop cap guidance: route non-safety polish to follow-up or escalation instead of another blind run_story/refresh cycle\n'
  fi
}

final_status_line() {
  local run_dir="$1"
  local manifest_file="$2"
  local changed_files_file="$3"
  local pytest_file="$4"
  local ai_review_file="$5"
  local classification_file="$6"
  local gate_result_file="$7"
  local raw_output_file="$8"
  local gate_decision gate_status recommendation pytest_exit_code codex_exit_code materialization_status changed_files_count changed_files_detected prereq_status
  local escalation_file escalation_status escalation_required resolution_action escalation_decision_source escalation_valid escalation_state
  local head_status expected_head current_head
  local ai_review_validation_state ai_review_validation_status ai_review_validation_code ai_review_validation_reason
  local previous_non_converging_run_dir reviewed_head checkout_head manual_finish_continuation_allowed
  local head_contract_state head_contract_code final_head_fidelity_state final_head_fidelity_status final_head_fidelity_code final_head_fidelity_reason
  local filtered_review_surface_status filtered_review_surface_code filtered_review_surface_reason
  local projection_state projection_status projection_code projection_reason

  gate_decision="$(json_value "$gate_result_file" "decision")"
  gate_status="$(json_value "$gate_result_file" "status")"
  recommendation="$(extract_merge_recommendation "$classification_file" 2>/dev/null || true)"
  pytest_exit_code="$(manifest_value "$manifest_file" "pytest_exit_code")"
  changed_files_detected="$(manifest_value "$manifest_file" "changed_files_detected")"
  codex_exit_code="$(manifest_value "$manifest_file" "codex_exit_code")"
  materialization_status="$(manifest_value "$manifest_file" "materialization_status")"
  prereq_status="$(review_prereq_status "$run_dir")"
  head_status="$(head_consistency_status "$manifest_file")"
  ai_review_validation_state="$(read_ai_review_artifact_state "$ai_review_file" "$raw_output_file" "$run_dir/chatgpt_review_prompt.md" 2>/dev/null || true)"
  IFS=$'\t' read -r ai_review_validation_status ai_review_validation_code ai_review_validation_reason <<<"$ai_review_validation_state"
  escalation_file="$run_dir/escalation_result.json"
  escalation_state="$(read_escalation_artifact_state "$escalation_file")"
  IFS=$'\x1f' read -r escalation_valid escalation_required escalation_status escalation_decision_source _ resolution_action <<<"$escalation_state"
  previous_non_converging_run_dir="$(detect_non_converging_rerun_for_run "$STORY_RUNS_ROOT" "$run_dir" || true)"
  reviewed_head="$(manifest_source_of_truth_head "$manifest_file")"
  checkout_head="$(current_checkout_head)"
  manual_finish_continuation_allowed="false"
  head_contract_state="$(resolve_review_head_contract "$STORY_RUNS_ROOT" "$run_dir" "$manifest_file")"
  IFS=$'\x1f' read -r _ head_contract_code _ _ _ _ <<<"$head_contract_state"
  if [[ "$head_contract_code" == "manual_finish_continuation_valid" ]]; then
    manual_finish_continuation_allowed="true"
    final_head_fidelity_state="$(review_artifact_fidelity_status "$run_dir" "$manifest_file")"
    IFS=$'\t' read -r final_head_fidelity_status final_head_fidelity_code final_head_fidelity_reason <<<"$final_head_fidelity_state"
  else
    final_head_fidelity_status=""
    final_head_fidelity_code=""
    final_head_fidelity_reason=""
  fi
  filtered_review_surface_status="valid"
  filtered_review_surface_code=""
  filtered_review_surface_reason=""
  projection_state="$(read_semantic_projection_artifact_state "$run_dir")"
  IFS=$'\t' read -r projection_status projection_code projection_reason <<<"$projection_state"
  refresh_metadata_state="$(read_refresh_evidence_metadata_state "$run_dir" "$STORY_ID")"
  IFS=$'\t' read -r refresh_metadata_status refresh_metadata_code refresh_metadata_reason <<<"$refresh_metadata_state"
  if [[ "$projection_status" == "invalid" ]]; then
    filtered_review_surface_status="invalid"
    filtered_review_surface_code="$projection_code"
    filtered_review_surface_reason="$projection_reason"
  elif [[ "$manual_finish_continuation_allowed" != "true" && "$prereq_status" == "ready" ]] \
    && { [[ "$projection_status" == "valid" ]] || run_manifest_companion_filter_enabled "$run_dir"; }; then
    if ! run_filtered_review_artifacts_match_recomputed_surface "$run_dir"; then
      filtered_review_surface_status="invalid"
      filtered_review_surface_code="review_surface_mismatch"
      filtered_review_surface_reason="filtered review artifacts are stale or inconsistent with recomputed baseline"
    fi
  fi

  if [[ -n "$previous_non_converging_run_dir" && "$head_status" == mismatch:* && "$manual_finish_continuation_allowed" != "true" ]]; then
    expected_head="${head_status#mismatch:}"
    current_head="${expected_head#*:}"
    expected_head="${expected_head%%:*}"
    printf 'RUN STATUS: BLOCKED (stale run evidence: manifest HEAD %s != current HEAD %s)\n' "$expected_head" "$current_head"
    return 0
  fi

  if [[ "$head_status" == mismatch:* && "$manual_finish_continuation_allowed" != "true" ]]; then
    expected_head="${head_status#mismatch:}"
    current_head="${expected_head#*:}"
    expected_head="${expected_head%%:*}"
    printf 'RUN STATUS: BLOCKED (stale run evidence: manifest HEAD %s != current HEAD %s)\n' "$expected_head" "$current_head"
    return 0
  fi

  loop_cap_final_stage="run_artifacts_ready"
  if [[ "$refresh_metadata_status" == "invalid" ]]; then
    loop_cap_final_stage="blocked_refresh_metadata_invalid"
  elif [[ "$filtered_review_surface_status" == "invalid" ]]; then
    loop_cap_final_stage="blocked_review_artifact_fidelity"
  elif [[ "$recommendation" == "reject" ]]; then
    loop_cap_final_stage="blocked_classification_rejected"
  elif [[ -f "$gate_result_file" && "$gate_decision" != "approve" ]]; then
    loop_cap_final_stage="blocked_review_gate_rejected"
  fi

  loop_cap_state="$(detect_same_head_stage_loop_cap_for_run "$STORY_RUNS_ROOT" "$run_dir" "$loop_cap_final_stage" || true)"
  if [[ -n "$loop_cap_state" ]]; then
    if stage_loop_cap_requires_narrow_safety_fix "$loop_cap_final_stage" "$run_dir"; then
      printf 'RUN STATUS: NARROW FIX REQUIRED (loop cap reached)\n'
    else
      printf 'RUN STATUS: ESCALATION REQUIRED (loop cap reached)\n'
    fi
    return 0
  fi

  if [[ "$manual_finish_continuation_allowed" != "true" && "$filtered_review_surface_status" == "invalid" ]]; then
    printf 'RUN STATUS: BLOCKED (%s)\n' "${filtered_review_surface_reason:-filtered review artifacts are stale or inconsistent with recomputed baseline}"
    return 0
  fi

  if [[ "$refresh_metadata_status" == "invalid" ]]; then
    printf 'RUN STATUS: BLOCKED (invalid refresh evidence metadata: %s)\n' "${refresh_metadata_code:-unknown}"
    return 0
  fi

  if [[ -f "$changed_files_file" ]]; then
    changed_files_count="$(sed '/^[[:space:]]*$/d' "$changed_files_file" | wc -l | tr -d ' ')"
  else
    changed_files_count=""
  fi

  if [[ "$gate_decision" == "approve" && "$gate_status" == "passed" ]]; then
    case "$head_contract_code" in
      review_head_missing)
        printf 'RUN STATUS: BLOCKED (cannot verify run evidence: manifest source-of-truth HEAD missing)\n'
        ;;
      checkout_head_unavailable)
        printf 'RUN STATUS: BLOCKED (cannot verify run evidence: checkout HEAD unavailable)\n'
        ;;
      review_head_match)
        if working_tree_is_clean; then
          printf 'RUN STATUS: READY FOR MERGE REVIEW (gate approve)\n'
        else
          printf 'RUN STATUS: BLOCKED (%s)\n' "$(dirty_tree_reason)"
        fi
        ;;
      manual_finish_continuation_valid)
        if [[ "$final_head_fidelity_status" == "ok" ]]; then
          if working_tree_is_clean; then
            printf 'RUN STATUS: READY FOR MERGE REVIEW (gate approve)\n'
          else
            printf 'RUN STATUS: BLOCKED (%s)\n' "$(dirty_tree_reason)"
          fi
        else
          printf 'RUN STATUS: BLOCKED (manual-finish continuation allowed but final-HEAD compliance is not proven: %s [%s])\n' \
            "$final_head_fidelity_reason" \
            "$final_head_fidelity_code"
        fi
        ;;
      review_head_mismatch)
        printf 'RUN STATUS: BLOCKED (stale run evidence: manifest HEAD %s != current HEAD %s)\n' \
          "$reviewed_head" \
          "$checkout_head"
        ;;
      *)
        printf 'RUN STATUS: BLOCKED (cannot verify run evidence: %s)\n' "$head_contract_code"
        ;;
    esac
    return 0
  fi

  if [[ -f "$gate_result_file" ]]; then
    if [[ -f "$escalation_file" ]] && ([[ "$escalation_valid" != "true" ]] || ! escalation_artifact_is_valid "$escalation_required" "$escalation_status" "$escalation_decision_source" "$resolution_action"); then
      printf 'RUN STATUS: BLOCKED (invalid escalation artifact)\n'
      return 0
    fi
    if [[ "$escalation_required" == "true" && "$escalation_status" != "resolved" ]]; then
      printf 'RUN STATUS: BLOCKED (escalation required; repeated reject stagnation)\n'
      return 0
    fi
    if [[ "$escalation_required" == "true" && "$escalation_status" == "resolved" && "$resolution_action" == "force-followup" ]]; then
      printf 'RUN STATUS: READY TO RUN FOLLOW-UP (escalation resolved: force-followup)\n'
      return 0
    fi
    if [[ "$escalation_required" == "true" && "$escalation_status" == "resolved" && "$resolution_action" == "accept-as-is" ]]; then
      printf 'RUN STATUS: BLOCKED (escalation resolved: accept-as-is)\n'
      return 0
    fi
    if [[ "$escalation_required" == "true" && "$escalation_status" == "resolved" && "$resolution_action" == "abort" ]]; then
      printf 'RUN STATUS: BLOCKED (escalation resolved: abort)\n'
      return 0
    fi
    printf 'RUN STATUS: BLOCKED (gate %s/%s)\n' "${gate_decision:-unknown}" "${gate_status:-unknown}"
    return 0
  fi

  if [[ -n "$codex_exit_code" && "$codex_exit_code" != "0" ]]; then
    printf 'RUN STATUS: BLOCKED (codex failing)\n'
    return 0
  fi

  if [[ -n "$materialization_status" && "$materialization_status" != "applied" && "$materialization_status" != "not_needed" ]]; then
    printf 'RUN STATUS: BLOCKED (materialization %s)\n' "$materialization_status"
    return 0
  fi

  if [[ -n "$pytest_exit_code" && "$pytest_exit_code" != "0" ]]; then
    printf 'RUN STATUS: BLOCKED (pytest failing)\n'
    return 0
  fi

  if [[ "$recommendation" == "reject" ]]; then
    printf 'RUN STATUS: BLOCKED (classification reject; inspect review findings)\n'
    return 0
  fi

  if [[ "$recommendation" == "approve" ]]; then
    if [[ "$prereq_status" != "ready" ]]; then
      printf 'RUN STATUS: BLOCKED (missing review prerequisites: %s)\n' "${prereq_status#missing:}"
    elif [[ "$head_status" == "unknown:manifest_head_missing" ]]; then
      printf 'RUN STATUS: BLOCKED (cannot verify run evidence: manifest source-of-truth HEAD missing)\n'
    elif [[ "$head_status" == unknown:current_head_unavailable:* ]]; then
      printf 'RUN STATUS: BLOCKED (cannot verify run evidence: checkout HEAD unavailable)\n'
    elif working_tree_is_clean; then
      printf 'RUN STATUS: READY TO RUN GATE (pinned artifacts ready; classification approve)\n'
    else
      printf 'RUN STATUS: BLOCKED (%s)\n' "$(dirty_tree_reason)"
    fi
    return 0
  fi

  if [[ -f "$classification_file" ]]; then
    printf 'RUN STATUS: CHECK REVIEW CLASSIFICATION (invalid recommendation)\n'
    return 0
  fi

  if [[ -f "$ai_review_file" && "$ai_review_validation_status" != "valid" ]]; then
    printf 'RUN STATUS: CHECK AI REVIEW OUTPUT (invalid artifact: %s)\n' "${ai_review_validation_code:-unknown}"
    return 0
  fi

  if [[ -f "$ai_review_file" ]]; then
    if [[ "$head_status" == "unknown:manifest_head_missing" ]]; then
      printf 'RUN STATUS: BLOCKED (cannot verify run evidence: manifest source-of-truth HEAD missing)\n'
    elif [[ "$head_status" == unknown:current_head_unavailable:* ]]; then
      printf 'RUN STATUS: BLOCKED (cannot verify run evidence: checkout HEAD unavailable)\n'
    elif working_tree_is_clean; then
      printf 'RUN STATUS: READY TO CLASSIFY (AI review present, no valid classification)\n'
    else
      printf 'RUN STATUS: BLOCKED (%s)\n' "$(dirty_tree_reason)"
    fi
    return 0
  fi

  if [[ "$changed_files_detected" == "no" || "$changed_files_count" == "0" ]]; then
    printf 'RUN STATUS: CHECK RUN OUTPUT (no changed files detected)\n'
    return 0
  fi

  if [[ -n "$previous_non_converging_run_dir" && "$manual_finish_continuation_allowed" != "true" ]]; then
    printf 'RUN STATUS: BLOCKED (non-converging rerun; manual finish required)\n'
    return 0
  fi

  if [[ "$manual_finish_continuation_allowed" == "true" && "$final_head_fidelity_status" == "reject" ]]; then
    printf 'RUN STATUS: BLOCKED (manual-finish continuation allowed but final-HEAD compliance is not proven: %s [%s])\n' \
      "$final_head_fidelity_reason" \
      "$final_head_fidelity_code"
    return 0
  fi

  if [[ "$prereq_status" != "ready" ]]; then
    printf 'RUN STATUS: BLOCKED (missing review prerequisites: %s)\n' "${prereq_status#missing:}"
    return 0
  fi

  if [[ "$ai_review_validation_status" == "invalid" && "$ai_review_validation_code" == "ai_review_normalization_failed" ]]; then
    printf 'RUN STATUS: BLOCKED (ai review normalization failed; inspect ai_review_raw_output.txt)\n'
    return 0
  fi

  printf 'RUN STATUS: INCOMPLETE (review artifacts not generated yet)\n'
}

[[ $# -eq 1 ]] || usage

STORY_ID="$1"
validate_story_id "$STORY_ID"

STORY_RUNS_ROOT="$RUNS_ROOT/$STORY_ID"
[[ -d "$STORY_RUNS_ROOT" ]] || fail "story run root not found for '$STORY_ID': $STORY_RUNS_ROOT"

RUN_DIR="$(resolve_target_run_dir "$STORY_RUNS_ROOT" "$RUN_DIR_OVERRIDE")"
RUN_ID="$(basename "$RUN_DIR")"

MANIFEST_FILE="$RUN_DIR/manifest.md"
CHANGED_FILES_FILE="$RUN_DIR/changed_files.txt"
PYTEST_FILE="$RUN_DIR/pytest.txt"
AI_REVIEW_FILE="$RUN_DIR/ai_review_result.md"
AI_REVIEW_RAW_OUTPUT_FILE="$RUN_DIR/ai_review_raw_output.txt"
CLASSIFICATION_FILE="$RUN_DIR/review_classification.md"
GATE_RESULT_FILE="$RUN_DIR/review_gate_result.json"

printf 'Story / Run / Directory\n'
printf 'Story: %s\n' "$STORY_ID"
printf 'Run: %s\n' "$RUN_ID"
printf 'Directory: %s\n' "$RUN_DIR"
printf '\n'

printf 'Artifact Presence\n'
for artifact_name in \
  manifest.md \
  run_meta.txt \
  diff.stat \
  changed_files.txt \
  pytest.txt \
  review_bundle.md \
  chatgpt_review_prompt.md \
  diff.patch \
  refresh_review_evidence.json \
  ai_review_raw_output.txt \
  ai_review_result.md \
  review_classification.md \
  review_gate_result.json \
  escalation_result.json
do
  if [[ -f "$RUN_DIR/$artifact_name" ]]; then
    printf '%s: yes\n' "$artifact_name"
  else
    printf '%s: no\n' "$artifact_name"
  fi
done
printf '\n'

printf 'Branch / Starting HEAD / Review Base\n'
printf 'Branch: %s\n' "$(display_value "$(manifest_value "$MANIFEST_FILE" "branch" || true)")"
printf 'Starting HEAD: %s\n' "$(display_value "$(manifest_value "$MANIFEST_FILE" "starting_head" || true)")"
printf 'Review Base: %s\n' "$(display_value "$(manifest_value "$MANIFEST_FILE" "review_base_ref" || true)")"
printf 'Evidence HEAD Consistency: %s\n' "$(format_head_consistency_status "$MANIFEST_FILE")"
printf 'Refresh mode: %s\n' "$(display_value "$(manifest_value "$MANIFEST_FILE" "refresh_mode" || true)")"
printf '\n'

printf 'Manifest Metadata\n'
printf 'Codex exit: %s\n' "$(display_value "$(manifest_value "$MANIFEST_FILE" "codex_exit_code" || true)")"
printf 'Materialization: %s\n' "$(display_value "$(manifest_value "$MANIFEST_FILE" "materialization_status" || true)")"
printf 'Changed files detected: %s\n' "$(display_value "$(manifest_value "$MANIFEST_FILE" "changed_files_detected" || true)")"
printf '\n'

printf 'Changed Files\n'
printf '%s' "$(summarize_changed_files "$CHANGED_FILES_FILE")"
printf '\n'

printf 'Pytest\n'
printf '%s' "$(summarize_pytest "$MANIFEST_FILE" "$PYTEST_FILE")"
printf '\n'

printf 'Review Pipeline\n'
summarize_review_pipeline "$RUN_DIR" "$AI_REVIEW_FILE" "$CLASSIFICATION_FILE" "$GATE_RESULT_FILE" "$AI_REVIEW_RAW_OUTPUT_FILE"
printf '\n'

printf 'Workflow Chaining / Resume\n'
summarize_workflow_resume \
  "$STORY_ID" \
  "$RUN_DIR" \
  "$MANIFEST_FILE" \
  "$CHANGED_FILES_FILE" \
  "$PYTEST_FILE" \
  "$AI_REVIEW_FILE" \
  "$CLASSIFICATION_FILE" \
  "$GATE_RESULT_FILE" \
  "$AI_REVIEW_RAW_OUTPUT_FILE"
printf '\n'

final_status_line \
  "$RUN_DIR" \
  "$MANIFEST_FILE" \
  "$CHANGED_FILES_FILE" \
  "$PYTEST_FILE" \
  "$AI_REVIEW_FILE" \
  "$CLASSIFICATION_FILE" \
  "$GATE_RESULT_FILE" \
  "$AI_REVIEW_RAW_OUTPUT_FILE"
