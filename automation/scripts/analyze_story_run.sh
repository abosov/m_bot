#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${AUTOMATION_ROOT_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
RUNS_ROOT="${AUTOMATION_RUNS_ROOT:-$ROOT_DIR/automation/runs}"
RUN_DIR_OVERRIDE="${AUTOMATION_RUN_DIR:-}"
STORY_ID=""

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

read_first_non_empty_line() {
  local file_path="$1"
  [[ -f "$file_path" ]] || return 0

  sed -n '/[^[:space:]]/ { s/^[[:space:]]*//; p; q; }' "$file_path"
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
  local classification_file="$1"
  local -a decisions=()
  local line normalized

  [[ -f "$classification_file" ]] || return 1

  while IFS= read -r line || [[ -n "$line" ]]; do
    normalized="$(
      printf '%s\n' "$line" \
        | tr '[:upper:]' '[:lower:]' \
        | sed -E 's/`//g; s/^[[:space:]]*[0-9]+[.)][[:space:]]*//; s/^[[:space:]]*[-*][[:space:]]*//; s/[[:space:]]+/ /g; s/^[[:space:]]+//; s/[[:space:]]+$//'
    )"

    if [[ "$normalized" =~ ^merge[[:space:]]+recommendation:[[:space:]]*(approve|reject)$ ]]; then
      decisions+=("${BASH_REMATCH[1]}")
    fi
  done < "$classification_file"

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
  local pytest_exit_code pytest_head

  pytest_exit_code="$(manifest_value "$manifest_file" "pytest_exit_code")"
  pytest_head="$(read_first_non_empty_line "$pytest_file")"

  if [[ -n "$pytest_exit_code" ]]; then
    case "$pytest_exit_code" in
      0) printf 'pass (exit 0';;
      *) printf 'fail (exit %s' "$pytest_exit_code";;
    esac
    if [[ -n "$pytest_head" ]]; then
      printf '; %s)\n' "$pytest_head"
    else
      printf '; output unavailable)\n'
    fi
    return 0
  fi

  if [[ -f "$pytest_file" ]]; then
    if [[ -n "$pytest_head" ]]; then
      printf 'artifact present (%s)\n' "$pytest_head"
    else
      printf 'artifact present (empty)\n'
    fi
  else
    printf 'missing\n'
  fi
}

summarize_review_pipeline() {
  local ai_review_file="$1"
  local classification_file="$2"
  local gate_result_file="$3"
  local ai_status classification_status gate_status recommendation decision status source

  if [[ -f "$ai_review_file" ]]; then
    ai_status="present"
  else
    ai_status="missing"
  fi

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

  printf 'AI review: %s\n' "$ai_status"
  printf 'Classification: %s\n' "$classification_status"
  printf 'Gate: %s\n' "$gate_status"
}

final_status_line() {
  local manifest_file="$1"
  local changed_files_file="$2"
  local pytest_file="$3"
  local ai_review_file="$4"
  local classification_file="$5"
  local gate_result_file="$6"
  local gate_decision gate_status recommendation pytest_exit_code codex_exit_code materialization_status changed_files_count changed_files_detected

  gate_decision="$(json_value "$gate_result_file" "decision")"
  gate_status="$(json_value "$gate_result_file" "status")"
  recommendation="$(extract_merge_recommendation "$classification_file" 2>/dev/null || true)"
  pytest_exit_code="$(manifest_value "$manifest_file" "pytest_exit_code")"
  changed_files_detected="$(manifest_value "$manifest_file" "changed_files_detected")"
  codex_exit_code="$(manifest_value "$manifest_file" "codex_exit_code")"
  materialization_status="$(manifest_value "$manifest_file" "materialization_status")"

  if [[ -f "$changed_files_file" ]]; then
    changed_files_count="$(sed '/^[[:space:]]*$/d' "$changed_files_file" | wc -l | tr -d ' ')"
  else
    changed_files_count=""
  fi

  if [[ "$gate_decision" == "approve" && "$gate_status" == "passed" ]]; then
    printf 'RUN STATUS: READY FOR MERGE REVIEW (gate approve)\n'
    return 0
  fi

  if [[ -f "$gate_result_file" ]]; then
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
    printf 'RUN STATUS: READY TO RUN GATE (classification approve)\n'
    return 0
  fi

  if [[ -f "$classification_file" ]]; then
    printf 'RUN STATUS: CHECK REVIEW CLASSIFICATION (invalid recommendation)\n'
    return 0
  fi

  if [[ -f "$ai_review_file" ]]; then
    printf 'RUN STATUS: READY TO CLASSIFY (AI review present, no valid classification)\n'
    return 0
  fi

  if [[ "$changed_files_detected" == "no" || "$changed_files_count" == "0" ]]; then
    printf 'RUN STATUS: CHECK RUN OUTPUT (no changed files detected)\n'
    return 0
  fi

  if [[ ! -f "$pytest_file" ]]; then
    printf 'RUN STATUS: INCOMPLETE (pytest artifact missing)\n'
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
  changed_files.txt \
  pytest.txt \
  ai_review_result.md \
  review_classification.md \
  review_gate_result.json
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
summarize_review_pipeline "$AI_REVIEW_FILE" "$CLASSIFICATION_FILE" "$GATE_RESULT_FILE"
printf '\n'

final_status_line \
  "$MANIFEST_FILE" \
  "$CHANGED_FILES_FILE" \
  "$PYTEST_FILE" \
  "$AI_REVIEW_FILE" \
  "$CLASSIFICATION_FILE" \
  "$GATE_RESULT_FILE"
