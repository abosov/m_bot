#!/usr/bin/env bash

story_stage_loop_manifest_value() {
  local manifest_file="$1"
  local key="$2"
  [[ -f "$manifest_file" ]] || return 0

  sed -n -E "s/^-[[:space:]]+${key}:[[:space:]]*(.*)$/\\1/p" "$manifest_file" | head -n 1
}

story_stage_loop_manifest_source_of_truth_head() {
  local manifest_file="$1"
  local starting_head isolated_worktree_head

  isolated_worktree_head="$(story_stage_loop_manifest_value "$manifest_file" "isolated_worktree_head")"
  if [[ "$isolated_worktree_head" =~ ^[0-9a-f]{40}$ ]]; then
    printf '%s\n' "$isolated_worktree_head"
    return 0
  fi

  starting_head="$(story_stage_loop_manifest_value "$manifest_file" "starting_head")"
  if [[ -n "$starting_head" ]]; then
    printf '%s\n' "$starting_head"
    return 0
  fi

  if [[ -n "$isolated_worktree_head" ]]; then
    printf '%s\n' "$isolated_worktree_head"
  fi
}

story_stage_loop_json_value() {
  local json_file="$1"
  local key="$2"
  [[ -f "$json_file" ]] || return 0

  sed -n -E "s/.*\"${key}\"[[:space:]]*:[[:space:]]*\"([^\"]*)\".*/\\1/p" "$json_file" | head -n 1
}

story_stage_loop_read_escalation_artifact_state() {
  local escalation_file="$1"

  python3 - "$escalation_file" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])

def no_dupes(pairs):
    data = {}
    for key, value in pairs:
        if key in data:
            raise ValueError(f"duplicate key: {key}")
        data[key] = value
    return data

try:
    payload = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=no_dupes)
except Exception:
    print("false\x1ffalse\x1f\x1f\x1f\x1f")
    raise SystemExit(0)

if not isinstance(payload, dict):
    print("false\x1ffalse\x1f\x1f\x1f\x1f")
    raise SystemExit(0)

required = payload.get("escalation_required")
status = payload.get("status")
decision_source = payload.get("decision_source")
resolution_action = payload.get("resolution_action")

if not isinstance(required, bool) or not isinstance(status, str):
    print("false\x1ffalse\x1f\x1f\x1f\x1f")
    raise SystemExit(0)

if decision_source is None:
    decision_source = ""
if resolution_action is None:
    resolution_action = ""

if not isinstance(decision_source, str) or not isinstance(resolution_action, str):
    print("false\x1ffalse\x1f\x1f\x1f\x1f")
    raise SystemExit(0)

print(
    "true\x1f%s\x1f%s\x1f%s\x1f%s"
    % (
        "true" if required else "false",
        status,
        decision_source,
        resolution_action,
    )
)
PY
}

story_stage_loop_run_has_gate_approved() {
  local run_dir="$1"
  local gate_result_file="$run_dir/review_gate_result.json"
  local gate_decision gate_status

  [[ -f "$gate_result_file" ]] || return 1
  gate_decision="$(story_stage_loop_json_value "$gate_result_file" "decision")"
  gate_status="$(story_stage_loop_json_value "$gate_result_file" "status")"
  [[ "$gate_decision" == "approve" && "$gate_status" == "passed" ]]
}

story_stage_loop_run_has_terminal_escalation_resolution() {
  local run_dir="$1"
  local escalation_file="$run_dir/escalation_result.json"
  local escalation_state escalation_valid escalation_required escalation_status resolution_action

  [[ -f "$escalation_file" ]] || return 1
  escalation_state="$(story_stage_loop_read_escalation_artifact_state "$escalation_file")"
  IFS=$'\x1f' read -r escalation_valid escalation_required escalation_status _ resolution_action <<<"$escalation_state"
  [[ "$escalation_valid" == "true" ]] || return 1
  [[ "$escalation_required" == "true" ]] || return 1
  [[ "$escalation_status" == "resolved" ]] || return 1
  [[ "$resolution_action" == "accept-as-is" || "$resolution_action" == "abort" || "$resolution_action" == "force-followup" ]]
}

story_stage_loop_refresh_evidence_attributable() {
  local run_dir="$1"
  local manifest_file="$run_dir/manifest.md"
  local refresh_file="$run_dir/refresh_review_evidence.json"
  local manifest_story_id manifest_refresh_mode manifest_head

  [[ -f "$manifest_file" ]] || return 1
  [[ -f "$refresh_file" ]] || return 1

  manifest_story_id="$(story_stage_loop_manifest_value "$manifest_file" "story_id")"
  manifest_refresh_mode="$(story_stage_loop_manifest_value "$manifest_file" "refresh_mode")"
  manifest_head="$(story_stage_loop_manifest_source_of_truth_head "$manifest_file")"

  [[ -n "$manifest_story_id" ]] || return 1
  [[ "$manifest_refresh_mode" == "no_codex_review_evidence_refresh" ]] || return 1
  [[ "$manifest_head" =~ ^[0-9a-f]{40}$ ]] || return 1

  python3 - "$refresh_file" "$manifest_story_id" "$manifest_head" <<'PYREFRESH'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
expected_story_id = sys.argv[2]
expected_head = sys.argv[3]

try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    raise SystemExit(1)

if not isinstance(payload, dict):
    raise SystemExit(1)

# This predicate is intentionally weaker than refresh metadata validity.
# US-AUTO-58 must count repeated invalid refresh-evidence churn, but only
# when the artifact is attributable to the same story and reviewed HEAD.
if payload.get("story_id") != expected_story_id:
    raise SystemExit(1)
if payload.get("refresh_mode") != "no_codex_review_evidence_refresh":
    raise SystemExit(1)
if payload.get("current_head") != expected_head:
    raise SystemExit(1)
PYREFRESH
}

story_stage_loop_run_participates() {
  local run_dir="$1"
  local manifest_file="$run_dir/manifest.md"
  local reviewed_head

  [[ -f "$manifest_file" ]] || return 1
  reviewed_head="$(story_stage_loop_manifest_source_of_truth_head "$manifest_file")"
  [[ -n "$reviewed_head" ]] || return 1

  story_stage_loop_run_has_gate_approved "$run_dir" && return 1
  story_stage_loop_run_has_terminal_escalation_resolution "$run_dir" && return 1

  if [[ -n "$(story_stage_loop_manifest_value "$manifest_file" "refresh_mode" || true)" ]]; then
    story_stage_loop_refresh_evidence_attributable "$run_dir" && return 0
    return 1
  fi

  if [[ -f "$run_dir/review_gate_result.json" ]] || [[ -f "$run_dir/review_classification.md" ]] || [[ -f "$run_dir/ai_review_result.md" ]]; then
    return 0
  fi

  [[ "$(story_stage_loop_manifest_value "$manifest_file" "changed_files_detected" || true)" == "yes" ]]
}

story_stage_loop_detect_same_head_cap_for_run() {
  local story_runs_root="$1"
  local current_run_dir="$2"
  local current_stage="$3"
  local current_manifest="$current_run_dir/manifest.md"
  local current_head current_run_id candidate_run_dir candidate_run_id candidate_head
  local count=0 run_ids=()
  local threshold="${STAGE_LOOP_CAP_THRESHOLD:-3}"

  case "$current_stage" in
    run_artifacts_ready|ai_review_completed|classification_approved|blocked_classification_rejected|blocked_review_gate_rejected|blocked_review_artifact_fidelity|blocked_refresh_metadata_invalid)
      ;;
    *)
      return 1
      ;;
  esac

  [[ -f "$current_manifest" ]] || return 1
  current_head="$(story_stage_loop_manifest_source_of_truth_head "$current_manifest")"
  [[ -n "$current_head" ]] || return 1
  current_run_id="$(basename "$current_run_dir")"

  while IFS= read -r candidate_run_dir; do
    [[ -n "$candidate_run_dir" ]] || continue
    candidate_run_id="$(basename "$candidate_run_dir")"
    [[ "$candidate_run_id" > "$current_run_id" ]] && continue

    candidate_head="$(story_stage_loop_manifest_source_of_truth_head "$candidate_run_dir/manifest.md")"
    [[ -n "$candidate_head" ]] || continue
    [[ "$candidate_head" == "$current_head" ]] || continue
    story_stage_loop_run_participates "$candidate_run_dir" || continue

    count=$((count + 1))
    run_ids+=("$candidate_run_id")
  done < <(find "$story_runs_root" -mindepth 1 -maxdepth 1 -type d -print 2>/dev/null | LC_ALL=C sort)

  (( count >= threshold )) || return 1
  printf '%s\x1f%s\x1f%s\n' "$count" "$current_head" "${run_ids[*]}"
}

story_stage_loop_detect_same_head_cap_for_head() {
  local story_runs_root="$1"
  local current_head="$2"
  local candidate_run_dir candidate_run_id candidate_head
  local count=0 run_ids=()
  local threshold="${STAGE_LOOP_CAP_THRESHOLD:-3}"

  [[ -d "$story_runs_root" ]] || return 1
  [[ "$current_head" =~ ^[0-9a-f]{40}$ ]] || return 1

  while IFS= read -r candidate_run_dir; do
    [[ -n "$candidate_run_dir" ]] || continue
    candidate_head="$(story_stage_loop_manifest_source_of_truth_head "$candidate_run_dir/manifest.md")"
    [[ -n "$candidate_head" ]] || continue
    [[ "$candidate_head" == "$current_head" ]] || continue
    story_stage_loop_run_participates "$candidate_run_dir" || continue

    candidate_run_id="$(basename "$candidate_run_dir")"
    count=$((count + 1))
    run_ids+=("$candidate_run_id")
  done < <(find "$story_runs_root" -mindepth 1 -maxdepth 1 -type d -print 2>/dev/null | LC_ALL=C sort)

  (( count >= threshold )) || return 1
  printf '%s\x1f%s\x1f%s\n' "$count" "$current_head" "${run_ids[*]}"
}
