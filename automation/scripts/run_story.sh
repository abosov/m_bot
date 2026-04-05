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
  [[ -f "$json_file" ]] || return 0

  python3 - "$json_file" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
SUPPORTED_ACTIONS = {"accept-as-is", "force-followup", "abort"}

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
elif data["resolution_action"] == "":
    print("empty")
elif data["resolution_action"].strip() == "":
    print("blank")
elif data["resolution_action"] in SUPPORTED_ACTIONS:
    print(f"supported:{data['resolution_action']}")
else:
    print(f"unknown:{json.dumps(data['resolution_action'])}")
PY
}

invalid_resolution_action_detail() {
  local resolution_action="${1:-}"

  case "$resolution_action" in
    missing)
      printf '%s\n' "missing resolution_action"
      return 0
      ;;
    non-string)
      printf '%s\n' "non-string resolution_action"
      return 0
      ;;
    empty)
      printf '%s\n' "empty resolution_action"
      return 0
      ;;
    blank)
      printf '%s\n' "whitespace-only resolution_action"
      return 0
      ;;
    supported:*)
      return 1
      ;;
    unknown:*)
      printf "unknown resolution_action %s\n" "${resolution_action#unknown:}"
      return 0
      ;;
  esac

  return 1
}

manifest_declares_escalation_artifact() {
  local run_dir="$1"
  local manifest_file="$run_dir/manifest.md"

  [[ -f "$manifest_file" ]] || return 1
  grep -Fqx -- "- escalation_result.json" "$manifest_file"
}

run_manifest_starting_head() {
  local run_dir="$1"
  local manifest_file="$run_dir/manifest.md"
  manifest_value "$manifest_file" "starting_head"
}

run_dir_matches_current_head() {
  local run_dir="$1"
  local current_head="$2"
  local starting_head=""

  [[ -n "$run_dir" ]] || return 1
  starting_head="$(run_manifest_starting_head "$run_dir")"
  [[ -n "$starting_head" ]] || return 1
  [[ "$starting_head" == "$current_head" ]]
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
      echo "Stage gate:"
      echo " - Review-stage: blocked until those story-artifact changes are committed or discarded."
      echo " - Rerun gate: blocked until commit/discard resolves the dirty state."
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
  local convergence_boundary previous_run_dir latest_run_dir stable_review_surface_run_dir

  echo "[INFO] Preflight: classifying dirty paths for $story_id" >&2
  ensure_story_artifacts_committed "$story_id"
  enforce_escalation_resolution "$story_id"
  if [[ -d "$story_runs_root" ]] && stable_review_surface_run_dir="$(detect_stable_review_surface_rerun "$story_runs_root" || true)" && [[ -n "$stable_review_surface_run_dir" ]]; then
    fail_stable_review_surface_rerun "$story_id" "$stable_review_surface_run_dir"
  fi
  if [[ -d "$story_runs_root" ]] && convergence_boundary="$(detect_non_converging_rerun "$story_runs_root" || true)" && [[ -n "$convergence_boundary" ]]; then
    local current_head stale_starting_head
    previous_run_dir="${convergence_boundary%%$'\n'*}"
    if [[ "$convergence_boundary" == *$'\n'* ]]; then
      latest_run_dir="${convergence_boundary#*$'\n'}"
    else
      latest_run_dir=""
    fi
    current_head="$(git -C "$ROOT_DIR" rev-parse HEAD 2>/dev/null || true)"

    if [[ -n "$latest_run_dir" ]] && [[ -n "$current_head" ]] && ! run_dir_matches_current_head "$latest_run_dir" "$current_head"; then
      stale_starting_head="$(run_manifest_starting_head "$latest_run_dir")"
      printf '[INFO] Ignoring stale rerun evidence for %s: %s does not match current HEAD %s\n' \
        "$story_id" \
        "$stale_starting_head" \
        "$current_head" >&2
    else
      fail_non_converging_rerun "$story_id" "$previous_run_dir" "$latest_run_dir"
    fi
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

run_manifest_companion_filter_enabled() {
  local run_dir="$1"
  local manifest_file="$run_dir/manifest.md"
  local companion_filter_mode

  [[ -f "$manifest_file" ]] || return 1
  companion_filter_mode="$(manifest_value "$manifest_file" "execution_companion_filter_mode")"
  [[ "$companion_filter_mode" == "enabled" ]]
}

COMPANION_FILTER_SCOPE_STORY_ID=""
COMPANION_FILTER_SCOPE_ENABLED="0"

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

    in_section && /^[[:space:]]*-[[:space:]]+/ {
      item = $0
      sub(/^[[:space:]]*-[[:space:]]+/, "", item)
      gsub(/`/, "", item)
      print item
    }
  ' "$file"
}

story_is_code_only_for_execution_filter() {
  local story_id="$1"
  local scope_file

  [[ -n "$story_id" ]] || return 1

  if [[ "$COMPANION_FILTER_SCOPE_STORY_ID" != "$story_id" ]]; then
    COMPANION_FILTER_SCOPE_STORY_ID="$story_id"
    COMPANION_FILTER_SCOPE_ENABLED="0"
    scope_file="$ROOT_DIR/automation/bundles/active/$story_id/02_file_scope.md"

    if [[ -f "$scope_file" ]] && ! extract_markdown_section_items "$scope_file" "allowed" \
      | grep -Eq '(^docs/|\.md$)'; then
      COMPANION_FILTER_SCOPE_ENABLED="1"
    fi
  fi

  [[ "$COMPANION_FILTER_SCOPE_ENABLED" == "1" ]]
}

is_execution_companion_artifact_path() {
  local story_id="$1"
  local path="$2"

  story_is_code_only_for_execution_filter "$story_id" || return 1

  case "$path" in
    docs/90_codex/epics/US-AUTO_REGISTRY.md)
      return 0
      ;;
  esac

  return 1
}

is_preflight_ignored_path() {
  local story_id="$1"
  local path="$2"

  if is_story_artifact_path "$story_id" "$path"; then
    return 0
  fi

  is_execution_companion_artifact_path "$story_id" "$path"
}

filter_preflight_ignored_diff() {
  local story_id="$1"
  local line file
  local skip=0

  while IFS= read -r line; do
    if [[ "$line" =~ ^diff\ --git\ a/(.+)\ b/(.+)$ ]]; then
      file="${BASH_REMATCH[1]}"
      if is_preflight_ignored_path "$story_id" "$file"; then
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

sorted_filtered_changed_files_to() {
  local story_id="$1"
  local changed_files_file="$2"
  local output_file="$3"
  local tmp
  local path

  tmp="$(mktemp)"

  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    if is_preflight_ignored_path "$story_id" "$path"; then
      continue
    fi
    printf '%s\n' "$path"
  done < "$changed_files_file" | LC_ALL=C sort -u > "$tmp"

  mv "$tmp" "$output_file"
}

resolve_run_review_artifact_base() {
  local manifest_file="$1"
  local review_artifact_base

  review_artifact_base="$(manifest_value "$manifest_file" "review_artifact_base")"
  [[ -n "$review_artifact_base" ]] || return 1

  git -C "$ROOT_DIR" rev-parse --verify "${review_artifact_base}^{commit}" 2>/dev/null || return 1
}

run_can_recompute_review_surface() {
  local run_dir="$1"
  local manifest_file="$run_dir/manifest.md"
  local review_artifact_base run_head

  [[ -f "$manifest_file" ]] || return 1
  review_artifact_base="$(resolve_run_review_artifact_base "$manifest_file" || true)"
  run_head="$(run_source_of_truth_head "$run_dir")"

  [[ "$review_artifact_base" =~ ^[0-9a-f]{40}$ ]] || return 1
  [[ "$run_head" =~ ^[0-9a-f]{40}$ ]]
}

recompute_filtered_changed_files_for_run_to() {
  local story_id="$1"
  local run_dir="$2"
  local output_file="$3"
  local manifest_file="$run_dir/manifest.md"
  local review_artifact_base run_head tmp

  [[ -f "$manifest_file" ]] || return 1

  review_artifact_base="$(resolve_run_review_artifact_base "$manifest_file" || true)"
  run_head="$(run_source_of_truth_head "$run_dir")"

  [[ "$review_artifact_base" =~ ^[0-9a-f]{40}$ ]] || return 1
  [[ "$run_head" =~ ^[0-9a-f]{40}$ ]] || return 1

  tmp="$(mktemp)"

  git -C "$ROOT_DIR" diff --name-only "$review_artifact_base" "$run_head" -- . "$EPHEMERAL_LEDGER_EXCLUDE_PATHSPEC" \
    | sed '/^$/d' \
    | while IFS= read -r path; do
        [[ -n "$path" ]] || continue
        if is_preflight_ignored_path "$story_id" "$path"; then
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

  if story_is_code_only_for_execution_filter "$story_id" && run_manifest_companion_filter_enabled "$run_dir"; then
    recompute_filtered_changed_files_for_run_to "$story_id" "$run_dir" "$output_file" || return 1
    return 0
  fi

  [[ -f "$changed_files_file" ]] || return 1
  sorted_filtered_changed_files_to "$story_id" "$changed_files_file" "$output_file"
}

effective_diff_patch_for_run_to() {
  local story_id="$1"
  local run_dir="$2"
  local output_file="$3"
  local diff_artifact="$run_dir/diff.patch"

  if story_is_code_only_for_execution_filter "$story_id" && run_manifest_companion_filter_enabled "$run_dir"; then
    recompute_filtered_diff_patch_for_run_to "$story_id" "$run_dir" "$output_file" || return 1
    return 0
  fi

  [[ -f "$diff_artifact" ]] || return 1
  filter_preflight_ignored_diff "$story_id" < "$diff_artifact" > "$output_file"
}

recompute_filtered_diff_patch_for_run_to() {
  local story_id="$1"
  local run_dir="$2"
  local output_file="$3"
  local manifest_file="$run_dir/manifest.md"
  local review_artifact_base run_head

  [[ -f "$manifest_file" ]] || return 1

  review_artifact_base="$(resolve_run_review_artifact_base "$manifest_file" || true)"
  run_head="$(run_source_of_truth_head "$run_dir")"

  [[ "$review_artifact_base" =~ ^[0-9a-f]{40}$ ]] || return 1
  [[ "$run_head" =~ ^[0-9a-f]{40}$ ]] || return 1

  git -C "$ROOT_DIR" diff "$review_artifact_base" "$run_head" -- . "$EPHEMERAL_LEDGER_EXCLUDE_PATHSPEC" \
    | filter_preflight_ignored_diff "$story_id" > "$output_file"
}

run_filtered_review_artifacts_match_recomputed_surface() {
  local run_dir="$1"
  local changed_files_artifact="$run_dir/changed_files.txt"
  local diff_artifact="$run_dir/diff.patch"
  local expected_changed_files normalized_changed_files expected_diff normalized_diff

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
  sorted_filtered_changed_files_to "$STORY_ID" "$changed_files_artifact" "$normalized_changed_files"

  if ! recompute_filtered_diff_patch_for_run_to "$STORY_ID" "$run_dir" "$expected_diff"; then
    rm -f "$expected_changed_files" "$normalized_changed_files" "$expected_diff" "$normalized_diff"
    return 1
  fi
  filter_preflight_ignored_diff "$STORY_ID" < "$diff_artifact" > "$normalized_diff"

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

run_has_nonempty_file() {
  local path="$1"

  [[ -f "$path" ]] || return 1
  [[ -n "$(sed '/^[[:space:]]*$/d' "$path")" ]]
}

json_file_is_valid_object() {
  local json_file="$1"
  [[ -f "$json_file" ]] || return 1

  python3 - "$json_file" <<'PY'
import json
import sys
from pathlib import Path

try:
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
except json.JSONDecodeError:
    raise SystemExit(1)

raise SystemExit(0 if isinstance(data, dict) else 1)
PY
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

  if story_is_code_only_for_execution_filter "$STORY_ID" && run_manifest_companion_filter_enabled "$run_dir"; then
    run_filtered_review_artifacts_match_recomputed_surface "$run_dir" || return 1
  fi

  [[ ! -f "$run_dir/ai_review_result.md" ]] || return 1
  [[ ! -f "$run_dir/review_classification.md" ]] || return 1
  [[ ! -f "$run_dir/review_gate_result.json" ]] || return 1
  [[ ! -f "$run_dir/escalation_result.json" ]] || return 1
}

run_has_stable_review_surface_evidence() {
  local run_dir="$1"
  local manifest_file="$run_dir/manifest.md"
  local codex_exit_code materialization_status pytest_exit_code changed_files_detected review_artifact_base

  [[ -f "$manifest_file" ]] || return 1

  codex_exit_code="$(manifest_value "$manifest_file" "codex_exit_code")"
  pytest_exit_code="$(manifest_value "$manifest_file" "pytest_exit_code")"
  materialization_status="$(manifest_value "$manifest_file" "materialization_status")"
  changed_files_detected="$(manifest_value "$manifest_file" "changed_files_detected")"
  review_artifact_base="$(manifest_value "$manifest_file" "review_artifact_base")"

  [[ "$codex_exit_code" == "0" ]] || return 1
  [[ "$pytest_exit_code" == "0" ]] || return 1
  [[ "$changed_files_detected" == "yes" ]] || return 1
  [[ "$materialization_status" == "applied" || "$materialization_status" == "not_needed" ]] || return 1
  [[ -n "$review_artifact_base" ]] || return 1
  run_has_nonempty_changed_files "$run_dir" || return 1

  run_has_nonempty_file "$run_dir/run_meta.txt" || return 1
  run_has_nonempty_file "$run_dir/pytest.txt" || return 1
  run_has_nonempty_file "$run_dir/diff.patch" || return 1
  run_has_nonempty_file "$run_dir/review_bundle.md" || return 1
  run_has_nonempty_file "$run_dir/chatgpt_review_prompt.md" || return 1
  run_has_nonempty_file "$run_dir/ai_review_result.md" || return 1
  run_has_nonempty_file "$run_dir/review_classification.md" || return 1
  json_file_is_valid_object "$run_dir/review_gate_result.json" || return 1

  if story_is_code_only_for_execution_filter "$STORY_ID" && run_manifest_companion_filter_enabled "$run_dir"; then
    run_filtered_review_artifacts_match_recomputed_surface "$run_dir" || return 1
  fi
}

changed_files_match() {
  local story_id="$1"
  local left_run_dir="$2"
  local right_run_dir="$3"
  local left_sorted right_sorted

  left_sorted="$(mktemp)"
  right_sorted="$(mktemp)"

  sorted_effective_changed_files_for_run_to "$story_id" "$left_run_dir" "$left_sorted" || {
    rm -f "$left_sorted" "$right_sorted"
    return 1
  }
  sorted_effective_changed_files_for_run_to "$story_id" "$right_run_dir" "$right_sorted" || {
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
  local story_id="$1"
  local left_run_dir="$2"
  local right_run_dir="$3"
  local left_diff right_diff

  left_diff="$(mktemp)"
  right_diff="$(mktemp)"

  effective_diff_patch_for_run_to "$story_id" "$left_run_dir" "$left_diff" || {
    rm -f "$left_diff" "$right_diff"
    return 1
  }
  effective_diff_patch_for_run_to "$story_id" "$right_run_dir" "$right_diff" || {
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
  local story_id="$1"
  local left_run_dir="$2"
  local right_run_dir="$3"

  changed_files_match "$story_id" "$left_run_dir" "$right_run_dir" || return 1
  if ! story_is_code_only_for_execution_filter "$story_id"; then
    return 0
  fi
  if ! run_manifest_companion_filter_enabled "$left_run_dir" && ! run_manifest_companion_filter_enabled "$right_run_dir"; then
    return 0
  fi
  diff_patch_match "$story_id" "$left_run_dir" "$right_run_dir" || return 1
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

  review_surfaces_match \
    "$STORY_ID" \
    "$previous_run_dir" \
    "$latest_run_dir" || return 1

  printf '%s\n%s\n' "$previous_run_dir" "$latest_run_dir"
}

detect_stable_review_surface_rerun() {
  local story_runs_root="$1"
  local latest_run_dir latest_head current_head

  latest_run_dir="$(resolve_latest_run_dir "$story_runs_root" || true)"
  [[ -n "$latest_run_dir" ]] || return 1

  run_has_stable_review_surface_evidence "$latest_run_dir" || return 1

  latest_head="$(run_source_of_truth_head "$latest_run_dir")"
  current_head="$(git -C "$ROOT_DIR" rev-parse HEAD 2>/dev/null || true)"

  [[ "$latest_head" =~ ^[0-9a-f]{40}$ ]] || return 1
  [[ "$current_head" =~ ^[0-9a-f]{40}$ ]] || return 1
  [[ "$latest_head" == "$current_head" ]] || return 1

  printf '%s\n' "$latest_run_dir"
}

fail_non_converging_rerun() {
  local story_id="$1"
  local previous_run_dir="$2"
  local latest_run_dir="$3"

  {
    echo "ERROR: run blocked for '$story_id' because the latest committed-head rerun did not converge"
    printf 'Previous rerun evidence: %s\n' "$previous_run_dir"
    printf 'Latest rerun evidence: %s\n' "$latest_run_dir"
    echo "Stage gate:"
    echo " - Review-stage: blocked until manual finish is committed on HEAD and the manual-finish continuation becomes the new review surface."
    echo " - Rerun gate: forbidden; manual-finish continuation is active until manual finish is complete."
    echo "Manual finish required:"
    echo " - Inspect the latest workspace-only changes and finish the story manually on the branch."
    echo " - Commit the manual-finish result to HEAD once the branch is in its intended final state."
    printf ' - Inspect pinned evidence: AUTOMATION_RUN_DIR=%q automation/scripts/analyze_story_run.sh %q\n' "$latest_run_dir" "$story_id"
    echo " - Do not rerun automation/scripts/run_story.sh again until manual finish is complete."
  } >&2
  exit 1
}

fail_stable_review_surface_rerun() {
  local story_id="$1"
  local latest_run_dir="$2"
  local current_head

  current_head="$(git -C "$ROOT_DIR" rev-parse HEAD 2>/dev/null || true)"

  {
    echo "ERROR: run blocked for '$story_id' because rerunning would not change the effective review surface"
    echo "Reason: unchanged_effective_review_surface_for_committed_head"
    printf 'Pinned evidence: %s\n' "$latest_run_dir"
    printf 'Current committed HEAD: %s\n' "$current_head"
    echo "Stage gate:"
    echo " - Review-stage: use the pinned evidence already recorded for this committed HEAD."
    echo " - Rerun gate: blocked until HEAD changes and the committed review surface becomes different."
    echo "Operator handoff:"
    printf ' - Inspect pinned evidence: AUTOMATION_RUN_DIR=%q automation/scripts/analyze_story_run.sh %q\n' "$latest_run_dir" "$story_id"
    echo " - Do not rerun automation/scripts/run_story.sh again unless you first commit a change that alters the review surface."
  } >&2
  exit 1
}

enforce_escalation_resolution() {
  local story_id="$1"
  local story_runs_root="$RUNS_ROOT/$story_id"
  local latest_run_dir escalation_file escalation_required escalation_status resolution_action decision_source
  local parsed_fields parse_error invalid_resolution_detail

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

  if invalid_resolution_detail="$(invalid_resolution_action_detail "$resolution_action")"; then
    fail_invalid_escalation_resolution \
      "$story_id" \
      "$latest_run_dir" \
      "$invalid_resolution_detail"
  fi

  case "$resolution_action" in
    supported:force-followup)
      return 0
      ;;
    supported:accept-as-is|supported:abort)
      {
        echo "ERROR: run blocked for '$story_id' because escalation was resolved as '${resolution_action#supported:}'"
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
