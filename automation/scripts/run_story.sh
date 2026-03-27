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
  [[ -f "$json_file" ]] || return 0

  python3 - "$json_file" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])

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

if "decision_source" not in data:
    fail("missing_decision_source")
if not isinstance(data["decision_source"], str):
    fail("non_string_decision_source")

print("ok")
print("true" if data["escalation_required"] else "false")
print(data["status"])
print(data["decision_source"])
if "resolution_action" not in data:
    print("missing")
elif not isinstance(data["resolution_action"], str):
    print("non-string")
else:
    print(data["resolution_action"])
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

is_blank_resolution_action() {
  local resolution_action="${1:-}"
  [[ -z "${resolution_action//[[:space:]]/}" ]]
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

  echo "[INFO] Preflight: classifying dirty paths for $story_id" >&2
  ensure_story_artifacts_committed "$story_id"
  enforce_escalation_resolution "$story_id"
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

enforce_escalation_resolution() {
  local story_id="$1"
  local story_runs_root="$RUNS_ROOT/$story_id"
  local latest_run_dir escalation_file escalation_required escalation_status resolution_action decision_source
  local parsed_fields parse_error

  [[ -d "$story_runs_root" ]] || return 0
  latest_run_dir="$(resolve_latest_run_dir "$story_runs_root" || true)"
  [[ -n "$latest_run_dir" ]] || return 0

  escalation_file="$latest_run_dir/escalation_result.json"
  if [[ ! -f "$escalation_file" ]]; then
    manifest_declares_escalation_artifact "$latest_run_dir" && \
      fail_invalid_escalation_resolution "$story_id" "$latest_run_dir" "missing required escalation artifact"
    return 0
  fi

  if ! parsed_fields="$(inspect_escalation_artifact_strict "$escalation_file")"; then
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
  decision_source="${parsed_lines[3]:-}"
  resolution_action="${parsed_lines[4]:-}"

  [[ "$escalation_required" == "true" ]] || return 0

  if [[ "$escalation_status" != "resolved" ]]; then
    {
      echo "ERROR: run blocked for '$story_id' because escalation is required for the latest rejected run"
      printf 'Required action: AUTOMATION_RUN_DIR=%q automation/scripts/escalate_story.sh %q %s\n' "$latest_run_dir" "$story_id" "<accept-as-is|force-followup|abort>"
      printf 'Inspect first: AUTOMATION_RUN_DIR=%q automation/scripts/analyze_story_run.sh %q\n' "$latest_run_dir" "$story_id"
    } >&2
    exit 1
  fi

  if [[ "$decision_source" != "repeated_reject_stagnation" ]]; then
    fail_invalid_escalation_resolution \
      "$story_id" \
      "$latest_run_dir" \
      "invalid decision_source '$decision_source'"
  fi

  if [[ "$resolution_action" == "missing" ]]; then
    fail_invalid_escalation_resolution "$story_id" "$latest_run_dir" "missing resolution_action"
  fi

  if [[ "$resolution_action" == "non-string" ]]; then
    fail_invalid_escalation_resolution "$story_id" "$latest_run_dir" "non-string resolution_action"
  fi

  if is_blank_resolution_action "$resolution_action"; then
    fail_invalid_escalation_resolution "$story_id" "$latest_run_dir" "blank resolution_action"
  fi

  if ! is_supported_resolution_action "$resolution_action"; then
    fail_invalid_escalation_resolution \
      "$story_id" \
      "$latest_run_dir" \
      "unknown resolution_action '$resolution_action'"
  fi

  case "$resolution_action" in
    force-followup)
      return 0
      ;;
    accept-as-is|abort)
      {
        echo "ERROR: run blocked for '$story_id' because escalation was resolved as '$resolution_action'"
        printf 'Inspect latest decision: AUTOMATION_RUN_DIR=%q automation/scripts/analyze_story_run.sh %q\n' "$latest_run_dir" "$story_id"
      } >&2
      exit 1
      ;;
    *)
      fail_invalid_escalation_resolution \
        "$story_id" \
        "$latest_run_dir" \
        "unknown resolution_action '$resolution_action'"
      ;;
  esac
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

run_preflight_stage "$STORY_ID"

echo "[INFO] Validating story bundle: $BUNDLE_DIR" >&2
"$VALIDATOR_SCRIPT" "$STORY_ID"

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
