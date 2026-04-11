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
  local prompt_file="${2:-}"

  python3 - "$review_file" "$prompt_file" <<'PY'
import sys
from difflib import SequenceMatcher
from pathlib import Path

path = Path(sys.argv[1])
prompt_path = Path(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] else None

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

normalize_ai_review_artifact_from_raw() {
  local raw_output_file="$1"
  local review_file="$2"

  python3 - "$raw_output_file" "$review_file" <<'PY'
import sys
import tempfile
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
    if normalized == "# AI Review":
        start_index = index
        break

if start_index is None:
    print(
        "invalid\tai_review_normalization_failed\tAI review raw output did not contain the required '# AI Review' section"
    )
    sys.exit(0)

first_nonempty_index = next((i for i, line in enumerate(lines) if line.lstrip("\ufeff").strip()), None)
if first_nonempty_index != start_index:
    print(
        "invalid\tai_review_normalization_failed\tAI review raw output contained unexpected content before the required '# AI Review' section"
    )
    sys.exit(0)

normalized_text = "\n".join(lines[start_index:]).rstrip()

review_path.parent.mkdir(parents=True, exist_ok=True)

with tempfile.NamedTemporaryFile(
    mode="w",
    encoding="utf-8",
    dir=str(review_path.parent),
    prefix=f".{review_path.name}.",
    suffix=".tmp",
    delete=False,
) as tmp:
    tmp.write(normalized_text + "\n")
    tmp_path = Path(tmp.name)

tmp_path.replace(review_path)
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

  projection_state="$(read_semantic_projection_artifact_state "$run_dir")"
  IFS=$'\t' read -r projection_status _ <<< "$projection_state"
  if [[ "$projection_status" == "valid" ]]; then
    reviewed_head="$(manifest_source_of_truth_head "$manifest_file")"
    checkout_head="$(current_checkout_head)"
    if [[ -n "$reviewed_head" && -n "$checkout_head" ]] && head_matches_expected "$reviewed_head" "$checkout_head"; then
      return 0
    fi
  fi
  if [[ "$projection_status" == "invalid" ]]; then
    return 1
  fi

  local changed_files_artifact="$run_dir/changed_files.txt"
  local review_changed_files_artifact="$run_dir/review_changed_files.txt"
  local diff_artifact="$run_dir/diff.patch"
  local expected_changed_files normalized_changed_files expected_diff normalized_diff

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
    reviewed_head="$(manifest_source_of_truth_head "$manifest_file")"
    checkout_head="$(current_checkout_head)"
    if [[ -n "$reviewed_head" && -n "$checkout_head" ]] && head_matches_expected "$reviewed_head" "$checkout_head"; then
      printf 'ok\tsemantic_projection_valid\tartifact fidelity verified via semantic projection\n'
      return 0
    fi
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

[[ $# -eq 1 ]] || usage

require_cmd "$CODEX_BIN"

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
  fail "AI review blocked for '$STORY_ID': $head_validation_reason"
fi

if [[ "$head_validation_code" != "manual_finish_continuation_valid" ]] && run_manifest_companion_filter_enabled "$LATEST_RUN_DIR"; then
  run_filtered_review_artifacts_match_recomputed_surface "$LATEST_RUN_DIR" || \
    fail "AI review blocked for '$STORY_ID': filtered review artifacts are stale or inconsistent with recomputed baseline"
fi

if [[ "$head_validation_code" == "manual_finish_continuation_valid" ]]; then
  fidelity_state="$(review_artifact_fidelity_status "$LATEST_RUN_DIR" "$MANIFEST_FILE")"
  IFS=$'\t' read -r fidelity_status fidelity_code fidelity_reason <<< "$fidelity_state"
  if [[ "$fidelity_status" == "reject" ]]; then
    fail "AI review blocked for '$STORY_ID': $fidelity_reason ($fidelity_code)"
  fi
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

validation_state="$(read_ai_review_artifact_state "$RESULT_FILE" "$PROMPT_FILE")"
IFS=$'\t' read -r validation_status validation_code validation_reason <<< "$validation_state"

if [[ "$validation_status" != "valid" ]]; then
  normalization_state="$(normalize_ai_review_artifact_from_raw "$RAW_OUTPUT_FILE" "$RESULT_FILE")"
  IFS=$'\t' read -r normalization_status normalization_code normalization_reason <<< "$normalization_state"

  if [[ "$normalization_status" == "valid" ]]; then
    validation_state="$(read_ai_review_artifact_state "$RESULT_FILE" "$PROMPT_FILE")"
    IFS=$'\t' read -r validation_status validation_code validation_reason <<< "$validation_state"
    if [[ "$validation_status" != "valid" ]]; then
      rm -f "$RESULT_FILE"
      fail "AI review completed but normalization failed (ai_review_normalization_failed): $validation_reason. Raw output: $RAW_OUTPUT_FILE"
    fi
  elif [[ "$validation_status" == "missing" ]]; then
    rm -f "$RESULT_FILE"
    fail "AI review completed but normalization failed ($normalization_code): $normalization_reason. Raw output: $RAW_OUTPUT_FILE"
  else
    rm -f "$RESULT_FILE"
    fail "AI review completed but normalization failed (ai_review_normalization_failed): $validation_reason. Normalization from raw also failed ($normalization_code): $normalization_reason. Raw output: $RAW_OUTPUT_FILE"
  fi
fi

printf 'AI review result written: %s\n' "$RESULT_FILE"
