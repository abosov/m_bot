#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${AUTOMATION_ROOT_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
RUNS_ROOT="${AUTOMATION_RUNS_ROOT:-$ROOT_DIR/automation/runs}"
RUN_DIR_OVERRIDE="${AUTOMATION_RUN_DIR:-}"
STORY_ID=""
EPHEMERAL_LEDGER_PATH="automation/story_change_ledger.jsonl"
EPHEMERAL_LEDGER_EXCLUDE_PATHSPEC=":(exclude)$EPHEMERAL_LEDGER_PATH"

# shellcheck source=automation/scripts/merge_recommendation_contract.sh
source "$SCRIPT_DIR/merge_recommendation_contract.sh"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

usage() {
  cat >&2 <<'EOF'
Usage:
  automation/scripts/analyze_story_run.sh STORY_ID

Example:
  automation/scripts/analyze_story_run.sh US-AUTO-19
  AUTOMATION_RUN_DIR=automation/runs/US-AUTO-19/2026-03-16_11-00-00 automation/scripts/analyze_story_run.sh US-AUTO-19
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

  status="$(head_consistency_status "$manifest_file")"
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
  local prereq_status

  prereq_status="$(review_prereq_status "$run_dir")"

  if [[ -f "$ai_review_file" ]]; then
    printf 'present\n'
    return 0
  fi

  if [[ "$prereq_status" != "ready" ]]; then
    printf 'missing (prerequisites %s)\n' "${prereq_status#missing:}"
    return 0
  fi

  if [[ -f "$raw_output_file" ]]; then
    printf 'failed (raw output only)\n'
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
  escalation_file="$run_dir/escalation_result.json"
  escalation_state="$(read_escalation_artifact_state "$escalation_file")"
  IFS=$'\x1f' read -r escalation_valid escalation_required escalation_status escalation_decision_source escalation_reason resolution_action <<<"$escalation_state"

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

  if [[ "$head_status" == mismatch:* ]]; then
    expected_head="${head_status#mismatch:}"
    current_head="${expected_head#*:}"
    expected_head="${expected_head%%:*}"
    stage="blocked_stale_run_evidence"
    latest_valid_stage="none"
    resume_safety="blocked"
    blocked_reason="manifest HEAD $expected_head does not match checkout HEAD $current_head"
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
  else
    stage="run_artifacts_ready"
    latest_valid_stage="run_artifacts_ready"
    next_command="$(resume_next_command "ai_review_story_run.sh" "$story_id" "$run_dir")"

    if [[ -f "$raw_output_file" && ! -f "$ai_review_file" ]]; then
      stage="blocked_ai_review_failed"
      latest_valid_stage="run_artifacts_ready"
      next_command="$(resume_next_command "ai_review_story_run.sh" "$story_id" "$run_dir")"
    elif [[ -f "$ai_review_file" ]]; then
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

  printf 'Current stage: %s\n' "$stage"
  printf 'Latest valid stage: %s\n' "$latest_valid_stage"
  printf 'Resume safety: %s\n' "$resume_safety"
  printf 'Next recommended command: %s\n' "$next_command"
  if [[ -n "$blocked_reason" ]]; then
    printf 'Blocked reason: %s\n' "$blocked_reason"
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

  gate_decision="$(json_value "$gate_result_file" "decision")"
  gate_status="$(json_value "$gate_result_file" "status")"
  recommendation="$(extract_merge_recommendation "$classification_file" 2>/dev/null || true)"
  pytest_exit_code="$(manifest_value "$manifest_file" "pytest_exit_code")"
  changed_files_detected="$(manifest_value "$manifest_file" "changed_files_detected")"
  codex_exit_code="$(manifest_value "$manifest_file" "codex_exit_code")"
  materialization_status="$(manifest_value "$manifest_file" "materialization_status")"
  prereq_status="$(review_prereq_status "$run_dir")"
  head_status="$(head_consistency_status "$manifest_file")"
  escalation_file="$run_dir/escalation_result.json"
  escalation_state="$(read_escalation_artifact_state "$escalation_file")"
  IFS=$'\x1f' read -r escalation_valid escalation_required escalation_status escalation_decision_source _ resolution_action <<<"$escalation_state"

  if [[ "$head_status" == mismatch:* ]]; then
    expected_head="${head_status#mismatch:}"
    current_head="${expected_head#*:}"
    expected_head="${expected_head%%:*}"
    printf 'RUN STATUS: BLOCKED (stale run evidence: manifest HEAD %s != current HEAD %s)\n' "$expected_head" "$current_head"
    return 0
  fi

  if [[ -f "$changed_files_file" ]]; then
    changed_files_count="$(sed '/^[[:space:]]*$/d' "$changed_files_file" | wc -l | tr -d ' ')"
  else
    changed_files_count=""
  fi

  if [[ "$gate_decision" == "approve" && "$gate_status" == "passed" ]]; then
    if [[ "$head_status" == "unknown:manifest_head_missing" ]]; then
      printf 'RUN STATUS: BLOCKED (cannot verify run evidence: manifest source-of-truth HEAD missing)\n'
    elif [[ "$head_status" == unknown:current_head_unavailable:* ]]; then
      printf 'RUN STATUS: BLOCKED (cannot verify run evidence: checkout HEAD unavailable)\n'
    elif working_tree_is_clean; then
      printf 'RUN STATUS: READY FOR MERGE REVIEW (gate approve)\n'
    else
      printf 'RUN STATUS: BLOCKED (%s)\n' "$(dirty_tree_reason)"
    fi
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

  if [[ "$prereq_status" != "ready" ]]; then
    printf 'RUN STATUS: BLOCKED (missing review prerequisites: %s)\n' "${prereq_status#missing:}"
    return 0
  fi

  if [[ -f "$raw_output_file" ]]; then
    printf 'RUN STATUS: BLOCKED (ai review failed; inspect ai_review_raw_output.txt)\n'
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
