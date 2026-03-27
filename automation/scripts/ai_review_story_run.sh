#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${AUTOMATION_ROOT_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
RUNS_ROOT="${AUTOMATION_RUNS_ROOT:-$ROOT_DIR/automation/runs}"
RUN_DIR_OVERRIDE="${AUTOMATION_RUN_DIR:-}"
CODEX_BIN="${CODEX_BIN:-codex}"
EPHEMERAL_LEDGER_PATH="automation/story_change_ledger.jsonl"
EPHEMERAL_LEDGER_EXCLUDE_PATHSPEC=":(exclude)$EPHEMERAL_LEDGER_PATH"

RESULT_FILE_NAME="ai_review_result.md"
RAW_OUTPUT_FILE_NAME="ai_review_raw_output.txt"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

usage() {
  cat >&2 <<'EOF'
Usage:
  automation/scripts/ai_review_story_run.sh STORY_ID

Example:
  automation/scripts/ai_review_story_run.sh US-AUTO-5
EOF
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "required command not found: $1"
}

read_ai_review_artifact_state() {
  local review_file="$1"

  python3 - "$review_file" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])

if not path.exists():
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

heading = normalized[first_nonempty_index]
if heading not in {"# AI Review", "# AI Review Result"}:
    print(
        "invalid\tai_review_malformed_artifact\tAI review artifact must start with '# AI Review' or '# AI Review Result'"
    )
    sys.exit(0)

body_lines = normalized[first_nonempty_index + 1 :]
substantive = [line for line in body_lines if line and not line.startswith("#")]
if not substantive:
    print(
        "invalid\tai_review_incomplete_artifact\tAI review artifact must include substantive review content after the heading"
    )
    sys.exit(0)

print("valid\tai_review_valid\tvalidated")
PY
}

normalize_ai_review_artifact_from_raw() {
  local raw_output_file="$1"
  local review_file="$2"

  python3 - "$raw_output_file" "$review_file" <<'PY'
import sys
from pathlib import Path

raw_path = Path(sys.argv[1])
review_path = Path(sys.argv[2])

if not raw_path.exists():
    print("invalid\tai_review_normalization_failed\tAI review raw output is missing; cannot normalize ai_review_result.md")
    sys.exit(0)

try:
    text = raw_path.read_text(encoding="utf-8")
except Exception:
    print("invalid\tai_review_normalization_failed\tAI review raw output could not be read as UTF-8 text")
    sys.exit(0)

if not text.strip():
    print("invalid\tai_review_normalization_failed\tAI review raw output is empty; cannot normalize ai_review_result.md")
    sys.exit(0)

lines = text.splitlines()
start_index = None
for index, line in enumerate(lines):
    normalized = line.lstrip("\ufeff").strip()
    if normalized in {"# AI Review", "# AI Review Result"}:
        start_index = index
        break

if start_index is None:
    print(
        "invalid\tai_review_normalization_failed\tAI review raw output did not contain a normalized '# AI Review' or '# AI Review Result' section"
    )
    sys.exit(0)

normalized_text = "\n".join(lines[start_index:]).rstrip()
review_path.write_text(normalized_text + "\n", encoding="utf-8")
print("valid\tai_review_normalized\tvalidated")
PY
}

working_tree_dirty() {
  local status_output
  status_output="$(git -C "$ROOT_DIR" status --porcelain --untracked-files=normal -- . "$EPHEMERAL_LEDGER_EXCLUDE_PATHSPEC" 2>/dev/null || true)"
  [[ -n "$status_output" ]]
}

fail_review_boundary_dirty_working_tree() {
  local story_id="$1"
  local run_dir="$2"
  {
    printf "ERROR: AI review blocked for '%s'\n" "$story_id"
    printf 'Reason: workspace-only changes would make review diverge from committed HEAD and origin/main...HEAD\n'
    printf 'Required action:\n'
    printf ' - inspect the workspace-only changes\n'
    printf ' - commit the changes if they belong in the reviewed diff, or discard them if they do not\n'
    printf ' - if you committed review-relevant changes, rerun automation/scripts/run_story.sh %s\n' "$story_id"
    printf ' - inspect the pinned run with AUTOMATION_RUN_DIR=%q automation/scripts/analyze_story_run.sh %q\n' "$run_dir" "$story_id"
    printf ' - rerun AUTOMATION_RUN_DIR=%q automation/scripts/ai_review_story_run.sh %q\n' "$run_dir" "$story_id"
  } >&2
  exit 1
}

validate_story_id() {
  local story_id="$1"
  [[ "$story_id" =~ ^US-[A-Z0-9]+(-[A-Z0-9]+)*$ ]] || \
    fail "invalid STORY_ID '$story_id' (expected format like US-AUTO-5)"
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

[[ $# -eq 1 ]] || usage

require_cmd "$CODEX_BIN"

STORY_ID="$1"
validate_story_id "$STORY_ID"

STORY_RUNS_ROOT="$RUNS_ROOT/$STORY_ID"
[[ -d "$STORY_RUNS_ROOT" ]] || fail "story run root not found for '$STORY_ID': $STORY_RUNS_ROOT"

LATEST_RUN_DIR="$(resolve_target_run_dir "$STORY_RUNS_ROOT" "$RUN_DIR_OVERRIDE")"

if working_tree_dirty; then
  fail_review_boundary_dirty_working_tree "$STORY_ID" "$LATEST_RUN_DIR"
fi

required_artifacts=(
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

RESULT_FILE="$LATEST_RUN_DIR/$RESULT_FILE_NAME"
RAW_OUTPUT_FILE="$LATEST_RUN_DIR/$RAW_OUTPUT_FILE_NAME"
PROMPT_FILE="$LATEST_RUN_DIR/chatgpt_review_prompt.md"

cmd=(
  "$CODEX_BIN"
  -a never
  exec
  -C "$ROOT_DIR"
  -s read-only
  -o "$RESULT_FILE"
)

if [[ -n "${CODEX_MODEL:-}" ]]; then
  cmd+=(-m "$CODEX_MODEL")
fi

if [[ -n "${CODEX_EXTRA_ARGS:-}" ]]; then
  # shellcheck disable=SC2206
  extra_args=( $CODEX_EXTRA_ARGS )
  cmd+=("${extra_args[@]}")
fi

cmd+=(-)

set +e
"${cmd[@]}" < "$PROMPT_FILE" >"$RAW_OUTPUT_FILE" 2>&1
review_exit_code=$?
set -e

if [[ $review_exit_code -ne 0 ]]; then
  rm -f "$RESULT_FILE"
  fail "AI review command failed for '$STORY_ID' (exit $review_exit_code). Raw output: $RAW_OUTPUT_FILE"
fi

validation_state="$(read_ai_review_artifact_state "$RESULT_FILE")"
IFS=$'\t' read -r validation_status validation_code validation_reason <<< "$validation_state"

if [[ "$validation_status" != "valid" ]]; then
  if [[ "$validation_status" == "missing" ]]; then
    normalization_state="$(normalize_ai_review_artifact_from_raw "$RAW_OUTPUT_FILE" "$RESULT_FILE")"
    IFS=$'\t' read -r normalization_status normalization_code normalization_reason <<< "$normalization_state"

    if [[ "$normalization_status" != "valid" ]]; then
      rm -f "$RESULT_FILE"
      fail "AI review completed but normalization failed ($normalization_code): $normalization_reason. Raw output: $RAW_OUTPUT_FILE"
    fi

    validation_state="$(read_ai_review_artifact_state "$RESULT_FILE")"
    IFS=$'\t' read -r validation_status validation_code validation_reason <<< "$validation_state"
    if [[ "$validation_status" != "valid" ]]; then
      rm -f "$RESULT_FILE"
      fail "AI review completed but produced an invalid normalized artifact ($validation_code): $validation_reason. Raw output: $RAW_OUTPUT_FILE"
    fi
  else
    rm -f "$RESULT_FILE"
    fail "AI review completed but produced an invalid artifact ($validation_code): $validation_reason. Raw output: $RAW_OUTPUT_FILE"
  fi
fi

printf 'AI review result written: %s\n' "$RESULT_FILE"
