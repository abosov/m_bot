#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${AUTOMATION_ROOT_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
BUNDLES_ROOT="${AUTOMATION_BUNDLES_ROOT:-$ROOT_DIR/automation/bundles/active}"
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
  local path

  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    [[ "$path" == "$EPHEMERAL_LEDGER_PATH" ]] && continue
    if is_story_artifact_path "$story_id" "$path"; then
      dirty_story_paths+=("$path")
    fi
  done < <(collect_dirty_paths)

  if (( ${#dirty_story_paths[@]} > 0 )); then
    {
      echo "ERROR: story artifacts for '$story_id' must be committed before run:"
      printf ' - %s\n' "${dirty_story_paths[@]}"
      echo "Remediation: $(commit_artifacts_command "$story_id")"
    } >&2
    exit 1
  fi
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
  local story_runs_root="$ROOT_DIR/automation/runs/$story_id"
  local latest_run_dir escalation_file escalation_required escalation_status resolution_action

  [[ -d "$story_runs_root" ]] || return 0
  latest_run_dir="$(resolve_latest_run_dir "$story_runs_root" || true)"
  [[ -n "$latest_run_dir" ]] || return 0

  escalation_file="$latest_run_dir/escalation_result.json"
  [[ -f "$escalation_file" ]] || return 0

  escalation_required="$(json_bool_value "$escalation_file" "escalation_required")"
  escalation_status="$(json_value "$escalation_file" "status")"
  resolution_action="$(json_value "$escalation_file" "resolution_action")"

  [[ "$escalation_required" == "true" ]] || return 0

  if [[ "$escalation_status" != "resolved" ]]; then
    {
      echo "ERROR: run blocked for '$story_id' because escalation is required for the latest rejected run"
      printf 'Required action: AUTOMATION_RUN_DIR=%q automation/scripts/escalate_story.sh %q %s\n' "$latest_run_dir" "$story_id" "<accept-as-is|force-followup|abort>"
      printf 'Inspect first: AUTOMATION_RUN_DIR=%q automation/scripts/analyze_story_run.sh %q\n' "$latest_run_dir" "$story_id"
    } >&2
    exit 1
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
      {
        echo "ERROR: run blocked for '$story_id' because resolved escalation artifact has invalid resolution_action '$resolution_action'"
        printf 'Inspect latest decision: AUTOMATION_RUN_DIR=%q automation/scripts/analyze_story_run.sh %q\n' "$latest_run_dir" "$story_id"
      } >&2
      exit 1
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

ensure_story_artifacts_committed "$STORY_ID"
enforce_escalation_resolution "$STORY_ID"

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
