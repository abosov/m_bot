#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${AUTOMATION_ROOT_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
RUNS_ROOT="${AUTOMATION_RUNS_ROOT:-$ROOT_DIR/automation/runs}"
RUN_DIR_OVERRIDE="${AUTOMATION_RUN_DIR:-}"
RULES_FILE="${CLASSIFICATION_RULES_FILE:-$ROOT_DIR/docs/90_codex/REVIEW_CLASSIFICATION_RULES.md}"
CODEX_BIN="${CODEX_BIN:-codex}"
EPHEMERAL_LEDGER_PATH="automation/story_change_ledger.jsonl"
EPHEMERAL_LEDGER_EXCLUDE_PATHSPEC=":(exclude)$EPHEMERAL_LEDGER_PATH"

AI_REVIEW_FILE_NAME="ai_review_result.md"
AI_REVIEW_RAW_OUTPUT_FILE_NAME="ai_review_raw_output.txt"
RESULT_FILE_NAME="review_classification.md"
RAW_OUTPUT_FILE_NAME="review_classification_raw_output.txt"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

usage() {
  cat >&2 <<'EOF'
Usage:
  automation/scripts/classify_review_story_run.sh STORY_ID

Example:
  automation/scripts/classify_review_story_run.sh US-AUTO-6
EOF
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "required command not found: $1"
}

require_file() {
  local path="$1"
  [[ -f "$path" ]] || fail "required file not found: $path"
}

clear_classification_artifacts() {
  local run_dir="$1"

  rm -f \
    "$run_dir/$RESULT_FILE_NAME" \
    "$run_dir/$RAW_OUTPUT_FILE_NAME"
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

working_tree_dirty() {
  local status_output
  status_output="$(git -C "$ROOT_DIR" status --porcelain --untracked-files=normal -- . "$EPHEMERAL_LEDGER_EXCLUDE_PATHSPEC" 2>/dev/null || true)"
  [[ -n "$status_output" ]]
}

fail_review_boundary_dirty_working_tree() {
  local story_id="$1"
  local run_dir="$2"
  {
    printf "ERROR: review classification blocked for '%s'\n" "$story_id"
    printf 'Reason: workspace-only changes would make review diverge from committed HEAD and origin/main...HEAD\n'
    printf 'Required action:\n'
    printf ' - inspect the workspace-only changes\n'
    printf ' - commit the changes if they belong in the reviewed diff, or discard them if they do not\n'
    printf ' - if you committed review-relevant changes, rerun automation/scripts/run_story.sh %s\n' "$story_id"
    printf ' - inspect the pinned run with AUTOMATION_RUN_DIR=%q automation/scripts/analyze_story_run.sh %q\n' "$run_dir" "$story_id"
    printf ' - rerun AUTOMATION_RUN_DIR=%q automation/scripts/classify_review_story_run.sh %q\n' "$run_dir" "$story_id"
  } >&2
  exit 1
}

validate_story_id() {
  local story_id="$1"
  [[ "$story_id" =~ ^US-[A-Z0-9]+(-[A-Z0-9]+)*$ ]] || \
    fail "invalid STORY_ID '$story_id' (expected format like US-AUTO-6)"
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

list_story_run_dirs() {
  local story_runs_root="$1"

  find "$story_runs_root" -mindepth 1 -maxdepth 1 -type d -print | LC_ALL=C sort
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

story_scope_file() {
  local story_id="$1"
  printf '%s\n' "$ROOT_DIR/automation/bundles/active/$story_id/02_file_scope.md"
}

scope_item_matches_path() {
  local item="${1#./}"
  local path="${2#./}"
  local prefix

  [[ -n "$item" ]] || return 1
  [[ "$item" == "$path" ]] && return 0

  if [[ "$item" == *"/**" ]]; then
    prefix="${item%/**}"
    [[ "$path" == "$prefix" ]] && return 0
    [[ "$path" == "$prefix/"* ]] && return 0
  fi

  return 1
}

is_path_explicitly_scope_approved() {
  local story_id="$1"
  local path="${2#./}"
  local scope_file item

  scope_file="$(story_scope_file "$story_id")"
  [[ -f "$scope_file" ]] || return 1

  while IFS= read -r item; do
    [[ -n "$item" ]] || continue
    if scope_item_matches_path "$item" "$path"; then
      return 0
    fi
  done < <(extract_markdown_section_items "$scope_file" "allowed")

  return 1
}

is_scope_approved_story_governance_artifact_path() {
  local story_id="$1"
  local path="${2#./}"

  case "$path" in
    "automation/bundle_packs/$story_id.bundle.md"|\
    "automation/bundles/active/$story_id"|\
    automation/bundles/active/$story_id/*|\
    "docs/90_codex/epics/US-AUTO_REGISTRY.md")
      is_path_explicitly_scope_approved "$story_id" "$path"
      return $?
      ;;
  esac

  return 1
}

is_non_runtime_companion_artifact_path() {
  local path="${1#./}"

  case "$path" in
    *)
      # Keep companion filtering fail-closed. Story governance artifacts are
      # handled separately and only when scope-approved.
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

  is_scope_approved_story_governance_artifact_path "$story_id" "$path"
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
  if [[ "$projection_status" == "invalid" ]]; then
    return 1
  fi

  if [[ "$projection_status" == "valid" ]]; then
    changed_files_artifact="$review_changed_files_artifact"
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

  [[ -f "$diff_artifact" ]] || printf 'reject\treview_diff_artifact_missing\trequired file not found: %s\n' "$diff_artifact"
  [[ -f "$diff_artifact" ]] || return 0
  [[ -f "$changed_files_artifact" ]] || printf 'reject\treview_changed_files_artifact_missing\trequired file not found: %s\n' "$changed_files_artifact"
  [[ -f "$changed_files_artifact" ]] || return 0

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

  :
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

validate_review_head_lineage() {
  local story_runs_root="$1"
  local run_dir="$2"
  local manifest_file="$3"
  local reviewed_head checkout_head

  reviewed_head="$(manifest_source_of_truth_head "$manifest_file")"
  [[ -n "$reviewed_head" ]] || return 0

  checkout_head="$(current_checkout_head)"
  if [[ -z "$checkout_head" ]]; then
    printf 'reject\treview_checkout_head_unavailable\tCurrent checkout HEAD is unavailable for reviewed HEAD %s\n' "$reviewed_head"
    return 0
  fi

  if head_matches_expected "$reviewed_head" "$checkout_head"; then
    printf 'allow\treview_head_match\tvalidated\n'
    return 0
  fi

  if strict_manual_finish_continuation_allowed "$story_runs_root" "$run_dir" "$reviewed_head" "$checkout_head"; then
    printf 'allow\tmanual_finish_continuation_valid\tvalidated\n'
    return 0
  fi

  printf 'reject\treview_head_mismatch\tReviewed HEAD %s does not match current checkout HEAD %s\n' "$reviewed_head" "$checkout_head"
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
  local -a normalized_lines=()
  local -a decisions=()
  local line normalized
  local i next_line

  while IFS= read -r line || [[ -n "$line" ]]; do
    normalized="$(
      printf '%s\n' "$line" \
        | tr '[:upper:]' '[:lower:]' \
        | sed -E 's/`//g; s/^[[:space:]]*[0-9]+[.)][[:space:]]*//; s/^[[:space:]]*[-*][[:space:]]*//; s/[[:space:]]+/ /g; s/^[[:space:]]+//; s/[[:space:]]+$//'
    )"
    normalized_lines+=("$normalized")
  done < "$classification_file"

  for (( i=0; i<${#normalized_lines[@]}; i++ )); do
    normalized="${normalized_lines[$i]}"

    if [[ "$normalized" =~ ^merge[[:space:]]+recommendation[^a-z]*(approve|reject)[^a-z]*$ ]]; then
      decisions+=("${BASH_REMATCH[1]}")
      continue
    fi

    if [[ "$normalized" =~ ^merge[[:space:]]+recommendation[^a-z]*$ ]]; then
      if (( i + 1 < ${#normalized_lines[@]} )); then
        next_line="${normalized_lines[$((i + 1))]}"
        if [[ "$next_line" =~ ^(approve|reject)$ ]]; then
          decisions+=("${BASH_REMATCH[1]}")
        fi
      fi
    fi
  done

  if (( ${#decisions[@]} == 0 )); then
    return 1
  fi

  local -a unique_decisions=()
  while IFS= read -r line; do
    [[ -n "$line" ]] && unique_decisions+=("$line")
  done < <(printf '%s\n' "${decisions[@]}" | LC_ALL=C sort -u)

  decisions=("${unique_decisions[@]}")
  [[ ${#decisions[@]} -eq 1 ]] || return 1

  printf '%s\n' "${decisions[0]}"
}
append_gate_contract() {
  local classification_file="$1"
  local merge_recommendation="$2"

  cat >>"$classification_file" <<EOF

## Review Gate Contract
MERGE RECOMMENDATION: $merge_recommendation
EOF
}

[[ $# -eq 1 ]] || usage

require_cmd "$CODEX_BIN"
require_file "$RULES_FILE"

STORY_ID="$1"
validate_story_id "$STORY_ID"

STORY_RUNS_ROOT="$RUNS_ROOT/$STORY_ID"
[[ -d "$STORY_RUNS_ROOT" ]] || fail "story run root not found for '$STORY_ID': $STORY_RUNS_ROOT"

LATEST_RUN_DIR="$(resolve_target_run_dir "$STORY_RUNS_ROOT" "$RUN_DIR_OVERRIDE")"
MANIFEST_FILE="$LATEST_RUN_DIR/manifest.md"

if working_tree_dirty; then
  fail_review_boundary_dirty_working_tree "$STORY_ID" "$LATEST_RUN_DIR"
fi

head_validation_state="$(validate_review_head_lineage "$STORY_RUNS_ROOT" "$LATEST_RUN_DIR" "$MANIFEST_FILE")"
IFS=$'\t' read -r head_validation_status head_validation_code head_validation_reason <<< "$head_validation_state"
if [[ "$head_validation_status" == "reject" ]]; then
  clear_classification_artifacts "$LATEST_RUN_DIR"
  fail "review classification blocked for '$STORY_ID': $head_validation_reason"
fi

projection_state="$(read_semantic_projection_artifact_state "$LATEST_RUN_DIR")"
IFS=$'\t' read -r projection_status projection_code projection_reason <<< "$projection_state"
if [[ "$projection_status" == "invalid" ]]; then
  clear_classification_artifacts "$LATEST_RUN_DIR"
  fail "review classification blocked for '$STORY_ID': $projection_reason ($projection_code)"
fi

if [[ "$head_validation_code" != "manual_finish_continuation_valid" ]] && { [[ "$projection_status" == "valid" ]] || run_manifest_companion_filter_enabled "$LATEST_RUN_DIR"; }; then
  if ! run_filtered_review_artifacts_match_recomputed_surface "$LATEST_RUN_DIR"; then
    clear_classification_artifacts "$LATEST_RUN_DIR"
    fail "review classification blocked for '$STORY_ID': filtered review artifacts are stale or inconsistent with recomputed baseline"
  fi
fi

if [[ "$head_validation_code" == "manual_finish_continuation_valid" ]]; then
  fidelity_state="$(review_artifact_fidelity_status "$LATEST_RUN_DIR" "$MANIFEST_FILE")"
  IFS=$'\t' read -r fidelity_status fidelity_code fidelity_reason <<< "$fidelity_state"
  if [[ "$fidelity_status" == "reject" ]]; then
    clear_classification_artifacts "$LATEST_RUN_DIR"
    fail "review classification blocked for '$STORY_ID': $fidelity_reason ($fidelity_code)"
  fi
fi

AI_REVIEW_FILE="$LATEST_RUN_DIR/$AI_REVIEW_FILE_NAME"
AI_REVIEW_RAW_OUTPUT_FILE="$LATEST_RUN_DIR/$AI_REVIEW_RAW_OUTPUT_FILE_NAME"
AI_REVIEW_PROMPT_FILE="$LATEST_RUN_DIR/chatgpt_review_prompt.md"
validation_state="$(read_ai_review_artifact_state "$AI_REVIEW_FILE" "$AI_REVIEW_RAW_OUTPUT_FILE" "$AI_REVIEW_PROMPT_FILE")"
IFS=$'\t' read -r validation_status validation_code validation_reason <<< "$validation_state"
if [[ "$validation_status" != "valid" ]]; then
  clear_classification_artifacts "$LATEST_RUN_DIR"
  fail "review classification blocked for '$STORY_ID': invalid AI review artifact ($validation_code): $validation_reason ($AI_REVIEW_FILE)"
fi

RESULT_FILE="$LATEST_RUN_DIR/$RESULT_FILE_NAME"
RAW_OUTPUT_FILE="$LATEST_RUN_DIR/$RAW_OUTPUT_FILE_NAME"

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

cmd+=(-)

set +e
{
  cat <<EOF
# ${STORY_ID} REVIEW CLASSIFICATION PROMPT

## ROLE
You are the Reviewer (Architect + QA + Security) for Zumbot.

## SOURCE OF TRUTH
- $RULES_FILE

## INPUT ARTIFACTS
- AI review result: $AI_REVIEW_FILE
- Latest run directory: $LATEST_RUN_DIR

## TASK
Classify every concrete finding from the AI review result using exactly one of:
- \`MERGE BLOCKER\`
- \`MINOR IMPROVEMENT\`
- \`FOLLOW-UP STORY\`

Follow the classification rules exactly. Do not invent findings that are not supported by the AI review result.

## OUTPUT FORMAT
Return:
1. findings by classification
2. required fixes before merge
3. optional improvements
4. follow-up stories to create
5. merge recommendation (\`approve\` or \`reject\`)

Include the final recommendation as an exact standalone line:
\`MERGE RECOMMENDATION: approve\`
or
\`MERGE RECOMMENDATION: reject\`

## CLASSIFICATION RULES
EOF
  cat "$RULES_FILE"
  cat <<EOF

## AI REVIEW RESULT
EOF
  cat "$AI_REVIEW_FILE"
} | "${cmd[@]}" >"$RAW_OUTPUT_FILE" 2>&1
classification_exit_code=$?
set -e

if [[ $classification_exit_code -ne 0 ]]; then
  rm -f "$RESULT_FILE"
  fail "review classification command failed for '$STORY_ID' (exit $classification_exit_code). Raw output: $RAW_OUTPUT_FILE"
fi

if [[ ! -s "$RESULT_FILE" ]]; then
  rm -f "$RESULT_FILE"
  fail "review classification completed but did not write a result artifact: $RESULT_FILE"
fi

if ! merge_recommendation="$(extract_merge_recommendation "$RESULT_FILE")"; then
  fail "review classification completed but did not produce a valid merge recommendation line in: $RESULT_FILE"
fi

append_gate_contract "$RESULT_FILE" "$merge_recommendation"

printf 'Merge recommendation: %s\n' "$merge_recommendation"
printf 'Review classification written: %s\n' "$RESULT_FILE"
