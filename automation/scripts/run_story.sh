#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${AUTOMATION_ROOT_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
BUNDLES_ROOT="${AUTOMATION_BUNDLES_ROOT:-$ROOT_DIR/automation/bundles/active}"
RUNS_ROOT="${AUTOMATION_RUNS_ROOT:-$ROOT_DIR/automation/runs}"
RUNNER="${AUTOMATION_RUNNER:-$ROOT_DIR/automation/run_codex_task.sh}"
VALIDATOR_SCRIPT="$ROOT_DIR/automation/scripts/validate_story_bundle.sh"
COMMIT_ARTIFACTS_HINT="automation/scripts/commit_story_artifacts.sh"
EPHEMERAL_LEDGER_PATH="automation/story_change_ledger.jsonl"
# shellcheck source=automation/scripts/story_change_ledger.sh
source "$SCRIPT_DIR/story_change_ledger.sh"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

commit_artifacts_command() {
  local story_id="$1"
  echo "$COMMIT_ARTIFACTS_HINT $story_id"
}

run_story_command() {
  local story_id="$1"
  echo "automation/scripts/run_story.sh $story_id"
}

usage() {
  cat >&2 <<'EOF'
Usage:
  automation/scripts/run_story.sh STORY_ID

Example:
  automation/scripts/run_story.sh US-AUTO-2
EOF
  exit 1
}

validate_story_id() {
  local story_id="$1"
  [[ "$story_id" =~ ^US-[A-Z0-9]+(-[A-Z0-9]+)*$ ]] || \
    fail "invalid STORY_ID '$story_id' (expected format like US-AUTO-2)"
}

require_file() {
  local path="$1"
  [[ -f "$path" ]] || fail "required file not found: $path"
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

json_has_string_key() {
  local json_file="$1"
  local key="$2"
  [[ -f "$json_file" ]] || return 1

  grep -q -E "\"${key}\"[[:space:]]*:[[:space:]]*\"" "$json_file"
}

inspect_escalation_artifact_strict() {
  local json_file="$1"
  local expected_story_id="$2"
  local expected_run_id="$3"
  local expected_run_dir="$4"
  local expected_gate_result="$5"
  [[ -f "$json_file" ]] || return 0

  python3 - "$json_file" "$expected_story_id" "$expected_run_id" "$expected_run_dir" "$expected_gate_result" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
expected_story_id = sys.argv[2]
expected_run_id = sys.argv[3]
expected_run_dir = sys.argv[4]
expected_gate_result = sys.argv[5]
SUPPORTED_ACTIONS = {"accept-as-is", "force-followup", "abort"}
ALLOWED_STATUSES = {"pending", "resolved"}
REQUIRED_DECISION_SOURCE = "repeated_reject_stagnation"

def fail(message: str) -> None:
    print(message)
    raise SystemExit(1)

def reject_dupes(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            fail("duplicate_key")
        out[key] = value
    return out

try:
    data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_dupes)
except json.JSONDecodeError:
    fail("malformed_json")

if not isinstance(data, dict):
    fail("non_object_json")

if "escalation_required" not in data:
    fail("missing_escalation_required")
if not isinstance(data["escalation_required"], bool):
    fail("non_boolean_escalation_required")

if "status" not in data:
    fail("missing_status")
if not isinstance(data["status"], str):
    fail("non_string_status")
if data["status"] not in ALLOWED_STATUSES:
    fail("invalid_status")

if "decision_source" not in data:
    fail("missing_decision_source")
if not isinstance(data["decision_source"], str):
    fail("non_string_decision_source")
if data["decision_source"] != REQUIRED_DECISION_SOURCE:
    fail("invalid_decision_source")

if "story_id" not in data:
    fail("missing_story_id")
if not isinstance(data["story_id"], str):
    fail("non_string_story_id")
if data["story_id"] != expected_story_id:
    fail("story_id_mismatch")

if "run_id" not in data:
    fail("missing_run_id")
if not isinstance(data["run_id"], str):
    fail("non_string_run_id")
if data["run_id"] != expected_run_id:
    fail("run_id_mismatch")

if "run_dir" not in data:
    fail("missing_run_dir")
if not isinstance(data["run_dir"], str):
    fail("non_string_run_dir")
if data["run_dir"] != expected_run_dir:
    fail("run_dir_mismatch")

if "gate_result" not in data:
    fail("missing_gate_result")
if not isinstance(data["gate_result"], str):
    fail("non_string_gate_result")
if data["gate_result"] != expected_gate_result:
    fail("gate_result_mismatch")

if "resolution_action" not in data:
    fail("missing_resolution_action")
if not isinstance(data["resolution_action"], str):
    fail("non_string_resolution_action")
if data["resolution_action"] == "":
    fail("empty_resolution_action")
if data["resolution_action"].strip() == "":
    fail("blank_resolution_action")
if data["resolution_action"] not in SUPPORTED_ACTIONS:
    fail("invalid_resolution_action")

status = data["status"]
resolution_action = data["resolution_action"]
escalation_required = data["escalation_required"]

if status == "pending":
    if escalation_required is not True:
        fail("pending_requires_escalation")
elif status == "resolved":
    if resolution_action == "force-followup":
        if escalation_required is not False:
            fail("resolved_force_followup_requires_nonblocking_escalation")
    elif resolution_action == "accept-as-is":
        if escalation_required is not False:
            fail("resolved_accept_as_is_requires_nonblocking_escalation")
    elif resolution_action == "abort":
        if escalation_required is not True:
            fail("resolved_abort_requires_escalation")
    else:
        fail("invalid_resolution_action")
else:
    fail("invalid_status")

print("ok")
print("true" if escalation_required else "false")
print(status)
print(resolution_action)
PY
}

manifest_declares_escalation_artifact() {
  local run_dir="$1"
  local manifest_file="$run_dir/manifest.md"

  [[ -f "$manifest_file" ]] || return 1
  grep -Fqx -- "- escalation_result.json" "$manifest_file"
}

fail_invalid_escalation_resolution() {
  local story_id="$1"
  local latest_run_dir="$2"
  local detail="$3"

  {
    echo "ERROR: run blocked for '$story_id' because escalation resolution is invalid: $detail"
    printf 'Fix the escalation artifact for this run before rerunning: %s\n' "$latest_run_dir/escalation_result.json"
    printf 'Inspect latest decision: AUTOMATION_RUN_DIR=%q automation/scripts/analyze_story_run.sh %q\n' "$latest_run_dir" "$story_id"
  } >&2
  exit 1
}

collect_dirty_paths() {
  {
    git -C "$ROOT_DIR" diff --name-only HEAD --
    git -C "$ROOT_DIR" ls-files --others --exclude-standard
  } | awk 'NF { print }' | sort -u
}

is_story_artifact_path() {
  local story_id="$1"
  local candidate="$2"

  [[ "$candidate" == "automation/bundle_packs/$story_id.bundle.md" ]] && return 0
  [[ "$candidate" == "automation/bundles/active/$story_id" ]] && return 0
  [[ "$candidate" == "automation/bundles/active/$story_id/"* ]] && return 0
  return 1
}

ensure_story_artifacts_committed() {
  local story_id="$1"
  local dirty_story_paths=()
  local unrelated_dirty_paths=()
  local path

  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    [[ "$path" == "$EPHEMERAL_LEDGER_PATH" ]] && continue
    if is_story_artifact_path "$story_id" "$path"; then
      dirty_story_paths+=("$path")
    else
      unrelated_dirty_paths+=("$path")
    fi
  done < <(collect_dirty_paths)

  if (( ${#unrelated_dirty_paths[@]} > 0 )); then
    {
      echo "ERROR: preflight blocked for '$story_id' because unrelated dirty paths exist:"
      printf ' - %s\n' "${unrelated_dirty_paths[@]}"
      if (( ${#dirty_story_paths[@]} > 0 )); then
        echo "Requested story artifact paths also remain dirty:"
        printf ' - %s\n' "${dirty_story_paths[@]}"
      fi
      echo "Resolve unrelated changes outside the story-artifact handoff flow."
      echo "Then rerun: $(run_story_command "$story_id")"
    } >&2
    exit 1
  fi

  if (( ${#dirty_story_paths[@]} > 0 )); then
    {
      echo "ERROR: preflight blocked for '$story_id' because requested story artifacts are dirty:"
      printf ' - %s\n' "${dirty_story_paths[@]}"
      echo "Operator handoff:"
      echo " - Review the requested story artifact changes."
      echo " - Run: $(commit_artifacts_command "$story_id")"
      echo " - Rerun: $(run_story_command "$story_id")"
    } >&2
    exit 1
  fi
}

run_preflight_stage() {
  local story_id="$1"
  local story_runs_root="$RUNS_ROOT/$story_id"
  local convergence_boundary previous_run_dir latest_run_dir

  echo "[INFO] Preflight: classifying dirty paths for $story_id" >&2
  ensure_story_artifacts_committed "$story_id"
  enforce_escalation_resolution "$story_id"
  if [[ -d "$story_runs_root" ]] && convergence_boundary="$(detect_non_converging_rerun "$story_runs_root" || true)" && [[ -n "$convergence_boundary" ]]; then
    IFS=$'\n' read -r previous_run_dir latest_run_dir <<< "$convergence_boundary"
    fail_non_converging_rerun "$story_id" "$previous_run_dir" "$latest_run_dir"
  fi
  echo "[INFO] Preflight: passed for $story_id" >&2
}

restore_ephemeral_story_change_ledger() {
  git -C "$ROOT_DIR" restore --worktree --source=HEAD -- "$EPHEMERAL_LEDGER_PATH" >/dev/null 2>&1 || true
}

cleanup_ephemeral_story_change_ledger() {
  restore_ephemeral_story_change_ledger
}

resolve_latest_run_dir() {
  local story_runs_root="$1"
  local latest_run_dir

  latest_run_dir="$(
    find "$story_runs_root" -mindepth 1 -maxdepth 1 -type d -print 2>/dev/null | LC_ALL=C sort | tail -n 1
  )"

  [[ -n "$latest_run_dir" ]] || return 1
  printf '%s\n' "$latest_run_dir"
}

resolve_dir_path() {
  local dir_path="$1"
  [[ -d "$dir_path" ]] || return 1
  (
    cd "$dir_path"
    pwd -P
  )
}

list_story_run_dirs() {
  local story_runs_root="$1"

  find "$story_runs_root" -mindepth 1 -maxdepth 1 -type d -print 2>/dev/null | LC_ALL=C sort
}

run_source_of_truth_head() {
  local run_dir="$1"
  local manifest_file="$run_dir/manifest.md"
  local isolated_worktree_head starting_head

  isolated_worktree_head="$(manifest_value "$manifest_file" "isolated_worktree_head")"
  if [[ "$isolated_worktree_head" =~ ^[0-9a-f]{40}$ ]]; then
    printf '%s\n' "$isolated_worktree_head"
    return 0
  fi

  starting_head="$(manifest_value "$manifest_file" "starting_head")"
  if [[ "$starting_head" =~ ^[0-9a-f]{40}$ ]]; then
    printf '%s\n' "$starting_head"
    return 0
  fi

  printf '\n'
}

run_has_nonempty_changed_files() {
  local run_dir="$1"
  local changed_files_file="$run_dir/changed_files.txt"

  [[ -f "$changed_files_file" ]] || return 1
  [[ -n "$(sed '/^[[:space:]]*$/d' "$changed_files_file")" ]]
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

  [[ ! -f "$run_dir/ai_review_result.md" ]] || return 1
  [[ ! -f "$run_dir/review_classification.md" ]] || return 1
  [[ ! -f "$run_dir/review_gate_result.json" ]] || return 1
  [[ ! -f "$run_dir/escalation_result.json" ]] || return 1
}

changed_files_match() {
  local left_file="$1"
  local right_file="$2"

  python3 - "$left_file" "$right_file" <<'PY'
import sys
from pathlib import Path

def normalized(path: Path) -> list[str]:
    return sorted(line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip())

raise SystemExit(0 if normalized(Path(sys.argv[1])) == normalized(Path(sys.argv[2])) else 1)
PY
}

detect_non_converging_rerun() {
  local story_runs_root="$1"
  local previous_run_dir latest_run_dir
  local previous_head latest_head current_head
  local run_dir
  local run_dirs=()

  while IFS= read -r run_dir; do
    run_dirs+=("$run_dir")
  done < <(list_story_run_dirs "$story_runs_root")

  (( ${#run_dirs[@]} >= 2 )) || return 1

  latest_run_dir="${run_dirs[${#run_dirs[@]}-1]}"
  previous_run_dir="${run_dirs[${#run_dirs[@]}-2]}"

  run_is_convergence_candidate "$previous_run_dir" || return 1
  run_is_convergence_candidate "$latest_run_dir" || return 1

  previous_head="$(run_source_of_truth_head "$previous_run_dir")"
  latest_head="$(run_source_of_truth_head "$latest_run_dir")"
  current_head="$(git -C "$ROOT_DIR" rev-parse HEAD 2>/dev/null || true)"

  [[ -n "$previous_head" && -n "$latest_head" ]] || return 1
  [[ "$previous_head" != "$latest_head" ]] || return 1

  if [[ -n "$current_head" && "$current_head" != "$latest_head" ]]; then
    if git -C "$ROOT_DIR" merge-base --is-ancestor "$latest_head" "$current_head" >/dev/null 2>&1; then
      return 1
    fi
  fi

  changed_files_match \
    "$previous_run_dir/changed_files.txt" \
    "$latest_run_dir/changed_files.txt" || return 1

  printf '%s\n%s\n' "$previous_run_dir" "$latest_run_dir"
}

fail_non_converging_rerun() {
  local story_id="$1"
  local previous_run_dir="$2"
  local latest_run_dir="$3"

  {
    echo "ERROR: run blocked for '$story_id' because the latest committed-head rerun did not converge"
    printf 'Previous rerun evidence: %s\n' "$previous_run_dir"
    printf 'Latest rerun evidence: %s\n' "$latest_run_dir"
    echo "Manual finish required:"
    echo " - Inspect the latest workspace-only changes and finish the story manually on the branch."
    echo " - Commit the manual-finish result to HEAD once the branch is in its intended final state."
    printf ' - Inspect pinned evidence: AUTOMATION_RUN_DIR=%q automation/scripts/analyze_story_run.sh %q\n' "$latest_run_dir" "$story_id"
    echo " - Do not rerun automation/scripts/run_story.sh again until manual finish is complete."
  } >&2
  exit 1
}

enforce_escalation_resolution() {
  local story_id="$1"
  local story_runs_root="$RUNS_ROOT/$story_id"
  local latest_run_dir latest_run_dir_resolved latest_run_id latest_gate_result escalation_file escalation_required
  local parsed_fields parse_error

  [[ -d "$story_runs_root" ]] || return 0
  latest_run_dir="$(resolve_latest_run_dir "$story_runs_root" || true)"
  [[ -n "$latest_run_dir" ]] || return 0
  latest_run_dir_resolved="$(resolve_dir_path "$latest_run_dir" || true)"
  [[ -n "$latest_run_dir_resolved" ]] || \
    fail_invalid_escalation_resolution "$story_id" "$latest_run_dir" "unable to resolve latest run directory"
  latest_run_id="$(basename "$latest_run_dir_resolved")"
  latest_gate_result="$latest_run_dir_resolved/review_gate_result.json"

  escalation_file="$latest_run_dir/escalation_result.json"
  if [[ ! -f "$escalation_file" ]]; then
    manifest_declares_escalation_artifact "$latest_run_dir" && \
      fail_invalid_escalation_resolution "$story_id" "$latest_run_dir" "missing required escalation artifact"
    return 0
  fi

  if ! parsed_fields="$(inspect_escalation_artifact_strict \
    "$escalation_file" \
    "$story_id" \
    "$latest_run_id" \
    "$latest_run_dir_resolved" \
    "$latest_gate_result"
  )"; then
    parse_error="$(printf '%s\n' "$parsed_fields" | tail -n 1)"
    parse_error="${parse_error//_/ }"
    fail_invalid_escalation_resolution "$story_id" "$latest_run_dir" "$parse_error"
  fi

  parsed_lines=()
  while IFS= read -r line; do
    parsed_lines+=("$line")
  done <<< "$parsed_fields"

  escalation_required="${parsed_lines[1]:-}"
  escalation_status="${parsed_lines[2]:-}"
  resolution_action="${parsed_lines[3]:-}"

  if [[ "$escalation_status" == "pending" ]]; then
    {
      echo "ERROR: run blocked for '$story_id' because escalation is required for the latest rejected run"
      printf 'Required action: AUTOMATION_RUN_DIR=%q automation/scripts/escalate_story.sh %q %s\n' "$latest_run_dir" "$story_id" "<accept-as-is|force-followup|abort>"
      printf 'Inspect first: AUTOMATION_RUN_DIR=%q automation/scripts/analyze_story_run.sh %q\n' "$latest_run_dir" "$story_id"
    } >&2
    exit 1
  fi

  if [[ "$escalation_status" == "resolved" && "$resolution_action" == "abort" ]]; then
    {
      echo "ERROR: run blocked for '$story_id' because escalation was resolved as 'abort'"
      printf 'Latest decision: %s\n' "$latest_run_dir/escalation_result.json"
      printf 'Inspect first: AUTOMATION_RUN_DIR=%q automation/scripts/analyze_story_run.sh %q\n' "$latest_run_dir" "$story_id"
    } >&2
    exit 1
  fi

  [[ "$escalation_required" == "true" ]] && \
    fail_invalid_escalation_resolution "$story_id" "$latest_run_dir" "resolved escalation cannot remain required"

  return 0
}

[[ $# -eq 1 ]] || usage
trap cleanup_ephemeral_story_change_ledger EXIT

STORY_ID="$1"
validate_story_id "$STORY_ID"

BUNDLE_DIR="$BUNDLES_ROOT/$STORY_ID"
MASTER_PROMPT="$BUNDLE_DIR/03_master_prompt.md"

[[ -d "$BUNDLE_DIR" ]] || fail "story bundle not found for '$STORY_ID': $BUNDLE_DIR"

required_files=(
  "00_story.md"
  "01_context_bundle.md"
  "02_file_scope.md"
  "03_master_prompt.md"
  "04_review_checklist.md"
  "05_followups.md"
  "06_manual_actions.md"
)

missing_files=()
for file_name in "${required_files[@]}"; do
  if [[ ! -f "$BUNDLE_DIR/$file_name" ]]; then
    missing_files+=("$BUNDLE_DIR/$file_name")
  fi
done

if (( ${#missing_files[@]} > 0 )); then
  {
    echo "ERROR: story bundle '$STORY_ID' is missing required files:"
    printf ' - %s\n' "${missing_files[@]}"
  } >&2
  exit 1
fi

require_file "$RUNNER"
require_file "$VALIDATOR_SCRIPT"
require_file "$MASTER_PROMPT"

echo "[INFO] Validating story bundle: $BUNDLE_DIR" >&2
"$VALIDATOR_SCRIPT" "$STORY_ID"

run_preflight_stage "$STORY_ID"

echo "[INFO] STORY_ID: $STORY_ID" >&2
echo "[INFO] Bundle dir: $BUNDLE_DIR" >&2
echo "[INFO] Master prompt: $MASTER_PROMPT" >&2
echo "[INFO] Delegating to: $RUNNER" >&2

append_story_change_ledger_entry \
  "$STORY_ID" \
  "story_started" \
  "started" \
  "" \
  "" \
  "" \
  "run_story" \
  "automation/bundles/active/$STORY_ID/03_master_prompt.md" \
  "run_story delegated to runner" || true

export AUTOMATION_STORY_START_LEDGER_RECORDED=1
set +e
"$RUNNER" "$MASTER_PROMPT"
runner_exit_code=$?
set -e

exit "$runner_exit_code"
