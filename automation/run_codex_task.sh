# file: automation/run_codex_task.sh
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)"
RUNNER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNS_ROOT="$ROOT_DIR/automation/runs"
DEFAULT_PROMPT_FILE="$ROOT_DIR/automation/prompts/current_task.md"
PROMPT_FILE="$DEFAULT_PROMPT_FILE"
CONTEXT_MODE="lean"
GENERATED_CONTEXT_FILES=()
REVIEW_BASE_REF="origin/main"
REVIEW_DIFF_RANGE="$REVIEW_BASE_REF...HEAD"
EPHEMERAL_LEDGER_PATH="automation/story_change_ledger.jsonl"
EPHEMERAL_LEDGER_EXCLUDE_PATHSPEC=":(exclude)$EPHEMERAL_LEDGER_PATH"
LEDGER_HELPER="$ROOT_DIR/automation/scripts/story_change_ledger.sh"

RUN_ID=""
RUN_DIR=""
WORKTREE_DIR=""
WORKTREE_HEAD=""
WORKTREE_CREATED="0"
ROLLBACK_BASE_HEAD=""
ROLLBACK_ARMED="1"

MANIFEST_FILE=""
STORY_CONTEXT_FILE=""
CODEX_PROMPT_FILE=""
REPOSITORY_MAP_RUNTIME_FILE=""
LOG_FILE=""
LAST_MESSAGE_FILE=""
DIFF_FILE=""
STAT_FILE=""
NAMEONLY_FILE=""
TEST_FILE=""
BUNDLE_FILE=""
REVIEW_PROMPT_FILE=""
META_FILE=""
CHECK_ALLOWED_FILES_SCRIPT=""
FALLBACK_CHECK_ALLOWED_FILES_SCRIPT=""
WORKTREE_TRACKED_LIST_FILE=""
WORKTREE_UNTRACKED_LIST_FILE=""
WORKTREE_COMPANION_TRACKED_LIST_FILE=""
WORKTREE_COMPANION_UNTRACKED_LIST_FILE=""
COMPANION_CONTAMINATION_DETECTED="0"
EXECUTION_COMPANION_FILTER_MODE="disabled"

MATERIALIZATION_STATUS="not_needed"
MATERIALIZED_TRACKED_COUNT="0"
MATERIALIZED_UNTRACKED_COUNT="0"
MATERIALIZED_CHANGE_COUNT="0"
REVIEW_ARTIFACT_BASE=""
REPOSITORY_MAP_RUNTIME_REL="repository_map_runtime.md"
REPOSITORY_MAP_INJECTION_STATUS="pending"
REPOSITORY_MAP_SOURCE_DOCS=""

BRANCH_NAME=""
CURRENT_HEAD=""
GIT_STATUS=""
PROMPT_CONTENT=""
SKIP_PYTEST="${SKIP_PYTEST:-0}"
PYTEST_TARGET="${PYTEST_TARGET:-}"
CODEX_MODEL="${CODEX_MODEL:-}"
CODEX_EXTRA_ARGS="${CODEX_EXTRA_ARGS:-}"
STORY_ID="ADHOC"
CONTEXT_FILES_CSV=""
CODEX_EXIT=""
PYTEST_EXIT=""
CHANGED_FILES=""
REVIEW_CHANGED_FILES_CONTENT=""
DIFF_STAT_CONTENT=""
PYTEST_OUTPUT_CONTENT=""
LAST_MESSAGE_CONTENT=""

RUN_STATUS="not_started"
SCOPE_PARSE_STATUS="not_applicable"
FILES_NOT_ALLOWED_PARSE_STATUS="not_applicable"

tracked_names_file=""
untracked_names_file=""
RUN_DIR_EXCLUDE_ENTRY=""

if [[ -f "$LEDGER_HELPER" ]]; then
  # shellcheck source=automation/scripts/story_change_ledger.sh
  source "$LEDGER_HELPER"
else
  append_story_change_ledger_entry() {
    return 0
  }
fi

write_run_meta() {
  [[ -n "${META_FILE:-}" ]] || return 0
  [[ -n "${RUN_DIR:-}" ]] || return 0
  mkdir -p "$RUN_DIR"

  cat > "$META_FILE" <<META
story_id=${STORY_ID:-ADHOC}
branch=${BRANCH_NAME:-}
head=${CURRENT_HEAD:-}
review_base_ref=${REVIEW_BASE_REF:-}
review_diff_range=${REVIEW_DIFF_RANGE:-}
prompt_file=${PROMPT_FILE:-}
run_dir=${RUN_DIR:-}
run_id=${RUN_ID:-}
timestamp_utc=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
status=${RUN_STATUS:-unknown}
scope_parse_status=${SCOPE_PARSE_STATUS:-unknown}
files_not_allowed_parse_status=${FILES_NOT_ALLOWED_PARSE_STATUS:-unknown}
materialization_status=${MATERIALIZATION_STATUS:-unknown}
materialized_tracked_changes=${MATERIALIZED_TRACKED_COUNT:-0}
materialized_untracked_files=${MATERIALIZED_UNTRACKED_COUNT:-0}
materialized_total_changes=${MATERIALIZED_CHANGE_COUNT:-0}
codex_exit_code=${CODEX_EXIT:-}
pytest_exit_code=${PYTEST_EXIT:-}
context_mode=${CONTEXT_MODE:-}
context_files=${CONTEXT_FILES_CSV:-}
repository_map_runtime_file=${REPOSITORY_MAP_RUNTIME_FILE:-}
repository_map_injection_status=${REPOSITORY_MAP_INJECTION_STATUS:-}
repository_map_source_docs=${REPOSITORY_MAP_SOURCE_DOCS:-}
skip_pytest=${SKIP_PYTEST:-0}
pytest_target=${PYTEST_TARGET:-}
codex_model=${CODEX_MODEL:-}
execution_companion_filter_mode=${EXECUTION_COMPANION_FILTER_MODE:-disabled}
isolated_run=true
isolated_worktree_dir=${WORKTREE_DIR:-}
isolated_worktree_head=${WORKTREE_HEAD:-}
isolated_worktree_cleanup=exit_trap
META
}

ensure_run_artifact_placeholders() {
  [[ -n "${RUN_DIR:-}" ]] || return 0
  mkdir -p "$RUN_DIR"
  [[ -n "${NAMEONLY_FILE:-}" ]] && : > "$NAMEONLY_FILE"
  [[ -n "${TEST_FILE:-}" ]] && : > "$TEST_FILE"
  write_run_meta
}

ensure_run_dir_gitignored() {
  local exclude_file rel_run_dir

  [[ -n "${RUN_DIR:-}" ]] || return 0
  exclude_file="$ROOT_DIR/.git/info/exclude"
  mkdir -p "$(dirname "$exclude_file")"

  rel_run_dir="${RUN_DIR#$ROOT_DIR/}"
  RUN_DIR_EXCLUDE_ENTRY="/$rel_run_dir/"

  touch "$exclude_file"
  if ! grep -Fqx "$RUN_DIR_EXCLUDE_ENTRY" "$exclude_file"; then
    printf '%s\n' "$RUN_DIR_EXCLUDE_ENTRY" >> "$exclude_file"
  fi
}

fail() {
  RUN_STATUS="failed"
  write_run_meta
  echo "ERROR: $*" >&2
  exit 1
}

info() {
  echo "[INFO] $*" >&2
}

warn() {
  echo "[WARN] $*" >&2
}

restore_ephemeral_story_change_ledger() {
  git -C "$ROOT_DIR" restore --worktree --source=HEAD -- "$EPHEMERAL_LEDGER_PATH" >/dev/null 2>&1 || true
}

usage() {
  cat <<EOF
Usage: $(basename "$0") [--full-context] [--lean-context] [prompt-file]

Options:
  --full-context  Include the full story bundle in story_context.md
  --lean-context  Include only the lean default bundle files in story_context.md
  -h, --help      Show this help message
EOF
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "required command not found: $1"
}

require_git_ref() {
  git rev-parse --verify --quiet "$1^{commit}" >/dev/null || fail "required git ref not found: $1"
}

derive_story_id() {
  local prompt_path="$1"
  local abs
  abs="$(cd "$(dirname "$prompt_path")" && pwd)/$(basename "$prompt_path")"

  if [[ "$abs" =~ /automation/bundles/active/([^/]+)/ ]]; then
    echo "${BASH_REMATCH[1]}"
    return 0
  fi

  local base
  base="$(basename "$prompt_path")"

  if [[ "$base" =~ (US-[A-Za-z0-9-]+) ]]; then
    echo "${BASH_REMATCH[1]}"
    return 0
  fi

  echo "ADHOC"
}

build_context_file_list() {
  local bundle_dir="$1"
  local mode="$2"

  case "$mode" in
    lean)
      printf '%s\n' \
        "$bundle_dir/03_master_prompt.md" \
        "$bundle_dir/00_story.md" \
        "$bundle_dir/02_file_scope.md"
      ;;
    full)
      printf '%s\n' \
        "$bundle_dir/00_story.md" \
        "$bundle_dir/01_context_bundle.md" \
        "$bundle_dir/02_file_scope.md" \
        "$bundle_dir/03_master_prompt.md" \
        "$bundle_dir/04_review_checklist.md" \
        "$bundle_dir/05_followups.md" \
        "$bundle_dir/06_manual_actions.md"
      ;;
    *)
      fail "unsupported context mode: $mode"
      ;;
  esac
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

emit_markdown_list_or_none() {
  local item

  if [[ $# -gt 0 ]]; then
    for item in "$@"; do
      echo "- $item"
    done
  else
    echo "- none"
  fi
}

generate_repository_map_runtime() {
  local out_file="$1"
  local curated_repo_map="$ROOT_DIR/docs/40_ai/zumbot_codex/REPOSITORY_MAP.md"
  local curated_project_context="$ROOT_DIR/docs/40_ai/zumbot_codex/PROJECT_CONTEXT.md"
  local story_id="${2:-}"
  local bundle_dir=""
  local scope_file=""
  local scope_parse_status="not_applicable"
  local blocked_scope_status="not_applicable"
  local -a source_docs=()
  local -a top_level_dirs=()
  local -a allowed_files=()
  local -a blocked_files=()
  local doc

  if [[ -n "$story_id" && "$story_id" != "ADHOC" ]]; then
    bundle_dir="$ROOT_DIR/automation/bundles/active/$story_id"
    scope_file="$bundle_dir/02_file_scope.md"

    if [[ -f "$scope_file" ]]; then
      while IFS= read -r doc; do
        [[ -n "$doc" ]] || continue
        allowed_files+=("$doc")
      done < <(extract_markdown_section_items "$scope_file" "allowed")

      while IFS= read -r doc; do
        [[ -n "$doc" ]] || continue
        blocked_files+=("$doc")
      done < <(extract_markdown_section_items "$scope_file" "blocked")

      if [[ ${#allowed_files[@]} -gt 0 ]]; then
        scope_parse_status="parsed"
      else
        scope_parse_status="unparseable"
      fi

      if [[ ${#blocked_files[@]} -gt 0 ]]; then
        blocked_scope_status="parsed"
      else
        blocked_scope_status="unavailable"
      fi
    elif [[ -d "$bundle_dir" ]]; then
      scope_parse_status="missing"
      blocked_scope_status="missing"
    fi
  fi

  SCOPE_PARSE_STATUS="$scope_parse_status"
  FILES_NOT_ALLOWED_PARSE_STATUS="$blocked_scope_status"

  for doc in "$curated_repo_map" "$curated_project_context"; do
    if [[ -f "$doc" ]]; then
      source_docs+=("${doc#$ROOT_DIR/}")
    fi
  done
  if [[ ${#source_docs[@]} -gt 0 ]]; then
    REPOSITORY_MAP_SOURCE_DOCS="$(printf '%s,' "${source_docs[@]}")"
    REPOSITORY_MAP_SOURCE_DOCS="${REPOSITORY_MAP_SOURCE_DOCS%,}"
  else
    REPOSITORY_MAP_SOURCE_DOCS=""
  fi

  while IFS= read -r doc; do
    [[ -n "$doc" ]] || continue
    top_level_dirs+=("$doc")
  done < <(git -C "$ROOT_DIR" ls-tree --name-only --full-tree -d HEAD | LC_ALL=C sort)

  {
    echo "# Repository Map Runtime"
    echo
    echo "Stable architectural context for this Codex run."
    echo
    echo "## Injection Status"
    echo "- status: injected"
    echo "- generation: lightweight deterministic runner artifact"
    echo
    echo "## Curated Source Docs"
    if [[ ${#source_docs[@]} -gt 0 ]]; then
      for doc in "${source_docs[@]}"; do
        echo "- $doc"
      done
    else
      echo "- none found"
    fi
    echo
    echo "## Top-Level Repository Directories"
    if [[ ${#top_level_dirs[@]} -gt 0 ]]; then
      for doc in "${top_level_dirs[@]}"; do
        echo "- $doc"
      done
    else
      echo "- none"
    fi
    echo
    echo "## Architecture Layers"
    echo "- API/Application: transport, validation, orchestration; keep business rules out."
    echo "- Domain/Services: own business rules, state transitions, and explicit product behavior."
    echo "- Infrastructure/Integrations: isolate DB, Telegram, Google Calendar, and external adapters."
    echo "- UI/Handlers: keep user-facing flows thin and preserve explicit contracts."
    echo "- Docs/Tests/Automation: update documentation and focused verification with implementation changes."
    echo
    echo "## Story-Local Context"
    echo "- story_id: ${story_id:-ADHOC}"
    if [[ -n "$bundle_dir" && -d "$bundle_dir" ]]; then
      echo "- active_bundle_path: ${bundle_dir#$ROOT_DIR/}"
      echo "- scope_file: ${scope_file#$ROOT_DIR/}"
      echo "- bundle_status: present"
    elif [[ -n "$bundle_dir" ]]; then
      echo "- active_bundle_path: ${bundle_dir#$ROOT_DIR/}"
      echo "- scope_file: ${scope_file#$ROOT_DIR/}"
      echo "- bundle_status: missing"
    else
      echo "- active_bundle_path: none"
      echo "- scope_file: none"
      echo "- bundle_status: not_applicable"
    fi
    echo "- scope_parse_status: $scope_parse_status"
    echo "- files_not_allowed_parse_status: $blocked_scope_status"
    if [[ "$scope_parse_status" == "parsed" ]]; then
      echo "- story_scope_constraints: loaded"
    else
      echo "- story_scope_constraints: unavailable"
    fi
    echo "- files_allowed_to_change:"
    if [[ "$scope_parse_status" == "parsed" ]]; then
      emit_markdown_list_or_none "${allowed_files[@]}"
    else
      echo "  unavailable"
    fi

    echo "- files_not_allowed_to_change:"
    if [[ "$blocked_scope_status" == "parsed" ]]; then
      emit_markdown_list_or_none "${blocked_files[@]}"
    else
      echo "  unavailable"
    fi
    echo
    echo "## Anti-Hallucination Rules"
    echo "- Do not invent files, modules, services, migrations, or tests that are not in the repository or story bundle."
    echo "- Do not broaden scope beyond the requested story and the allowed file set."
    echo "- Edit only files allowed for this story; treat listed forbidden files and untouched areas as read-only."
    echo "- If source-of-truth docs or bundle constraints conflict, stop and report before making broad changes."
    echo "- Prefer existing architecture, naming, and tests over new abstractions."
    echo
    echo "## Pipeline Dependency Hints"
    echo "- This artifact is generated by automation/run_codex_task.sh before Codex execution."
    echo "- story_context.md references this runtime map and includes selected bundle files for the same run."
    echo "- codex_prompt.md embeds this runtime map plus the requested task prompt."
    echo "- changed_files.txt is validated against automation/bundles/active/<story>/02_file_scope.md after materialization."
    echo "- manifest.md and run_meta.txt record repository map injection metadata for downstream review artifacts."

    if [[ -f "$curated_project_context" ]]; then
      echo
      echo "## Curated Project Context"
      echo
      cat "$curated_project_context"
    fi

    if [[ -f "$curated_repo_map" ]]; then
      echo
      echo "## Curated Repository Map"
      echo
      cat "$curated_repo_map"
    fi
  } > "$out_file"
}

generate_story_context() {
  local story_id="$1"
  local out_file="$2"
  local mode="$3"
  local repository_map_runtime_rel="${4:-repository_map_runtime.md}"
  local bundle_dir="$ROOT_DIR/automation/bundles/active/$story_id"
  GENERATED_CONTEXT_FILES=()

  if [[ ! -d "$bundle_dir" ]]; then
    cat > "$out_file" <<CTX
# Story Context

No active story bundle found for story id: $story_id

Requested context mode: $mode

Repository map artifact:
- $repository_map_runtime_rel

Expected bundle path:
$bundle_dir
CTX
    return 0
  fi

  local -a candidate_files=()
  local f
  while IFS= read -r f; do
    candidate_files+=("$f")
  done < <(build_context_file_list "$bundle_dir" "$mode")

  local rel
  for f in "${candidate_files[@]}"; do
    if [[ -f "$f" ]]; then
      GENERATED_CONTEXT_FILES+=("${f#$bundle_dir/}")
    fi
  done

  {
    echo "# Story Context"
    echo
    echo "Context mode: $mode"
    echo
    echo "Repository map artifact:"
    echo "- $repository_map_runtime_rel"
    echo
    echo "Included bundle files:"
    if [[ ${#GENERATED_CONTEXT_FILES[@]} -gt 0 ]]; then
      for rel in "${GENERATED_CONTEXT_FILES[@]}"; do
        echo "- $rel"
      done
    else
      echo "- none"
    fi
    echo
    for f in "${candidate_files[@]}"; do
      if [[ -f "$f" ]]; then
        echo "## $(basename "$f")"
        echo
        cat "$f"
        echo
      fi
    done
  } > "$out_file"
}

build_codex_prompt() {
  local out_file="$1"
  local repository_map_runtime_rel="$2"

  {
    echo "# Codex Runtime Prompt"
    echo
    echo "Read the runtime repository map before implementing the requested change."
    echo
    echo "Repository map artifact: $repository_map_runtime_rel"
    echo
    cat "$REPOSITORY_MAP_RUNTIME_FILE"
    echo
    echo "## Requested Task"
    echo
    printf '%s\n' "$PROMPT_CONTENT"
  } > "$out_file"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --full-context)
      CONTEXT_MODE="full"
      ;;
    --lean-context)
      CONTEXT_MODE="lean"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    -*)
      fail "unknown option: $1"
      ;;
    *)
      if [[ "$PROMPT_FILE" != "$DEFAULT_PROMPT_FILE" ]]; then
        fail "multiple prompt files provided"
      fi
      PROMPT_FILE="$1"
      ;;
  esac
  shift
done

if [[ $# -gt 0 ]]; then
  if [[ "$PROMPT_FILE" != "$DEFAULT_PROMPT_FILE" ]]; then
    fail "multiple prompt files provided"
  fi
  PROMPT_FILE="$1"
  shift
fi

[[ $# -eq 0 ]] || fail "unexpected arguments: $*"

require_cmd git
require_cmd bash
require_cmd codex
require_cmd pytest
require_cmd python3
require_cmd mktemp
require_git_ref "$REVIEW_BASE_REF"

[[ -f "$PROMPT_FILE" ]] || fail "prompt file not found: $PROMPT_FILE"

BRANCH_NAME="$(git rev-parse --abbrev-ref HEAD)"
CURRENT_HEAD="$(git rev-parse --short HEAD)"
GIT_STATUS="$(git status --porcelain -- . "$EPHEMERAL_LEDGER_EXCLUDE_PATHSPEC" || true)"
PROMPT_CONTENT="$(cat "$PROMPT_FILE")"

[[ "$BRANCH_NAME" != "main" ]] || fail "do not run automation on main; switch to a feature branch first"
[[ -z "$GIT_STATUS" ]] || fail "working tree is not clean; commit/stash changes first"
[[ -n "$PROMPT_CONTENT" ]] || fail "prompt file is empty: $PROMPT_FILE"

STORY_ID="$(derive_story_id "$PROMPT_FILE")"

if [[ "${AUTOMATION_STORY_START_LEDGER_RECORDED:-0}" != "1" ]]; then
  append_story_change_ledger_entry \
    "$STORY_ID" \
    "story_started" \
    "started" \
    "" \
    "$BRANCH_NAME" \
    "" \
    "automation/run_codex_task.sh" \
    "${PROMPT_FILE#$ROOT_DIR/}" \
    "runner started without run_story wrapper" || true
fi

RUN_ID="$(date -u +"%Y-%m-%d_%H-%M-%S")"
RUN_DIR="$RUNS_ROOT/$STORY_ID/$RUN_ID"

ROLLBACK_BASE_HEAD="$(git rev-parse HEAD)"
ROLLBACK_ARMED="1"
mkdir -p "$RUN_DIR"

MANIFEST_FILE="$RUN_DIR/manifest.md"
STORY_CONTEXT_FILE="$RUN_DIR/story_context.md"
CODEX_PROMPT_FILE="$RUN_DIR/codex_prompt.md"
REPOSITORY_MAP_RUNTIME_FILE="$RUN_DIR/repository_map_runtime.md"
LOG_FILE="$RUN_DIR/codex.log"
LAST_MESSAGE_FILE="$RUN_DIR/codex_last_message.txt"

COMPANION_FILTER_SCOPE_STORY_ID=""
COMPANION_FILTER_SCOPE_ENABLED="0"

is_story_artifact_ignored_path() {
  local story_id="$1"
  local path="$2"

  [[ "$path" == "automation/bundle_packs/$story_id.bundle.md" ]] && return 0
  [[ "$path" == "automation/bundles/active/$story_id" ]] && return 0
  [[ "$path" == "automation/bundles/active/$story_id/"* ]] && return 0
  return 1
}

path_exists_in_head() {
  local rel_path="$1"

  git cat-file -e "HEAD:$rel_path" >/dev/null 2>&1
}

story_is_code_only_for_execution_filter() {
  local story_id="$1"
  local scope_file

  [[ -n "$story_id" && "$story_id" != "ADHOC" ]] || return 1

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

is_execution_diff_ignored_path() {
  local story_id="$1"
  local path="$2"

  if is_story_artifact_ignored_path "$story_id" "$path"; then
    return 0
  fi

  is_execution_companion_artifact_path "$story_id" "$path"
}

filter_ignored_execution_diff_paths() {
  local story_id="$1"
  local line
  local file=""
  local skip=0

  while IFS= read -r line; do
    if [[ "$line" =~ ^diff\ --git\ a/(.+)\ b/(.+)$ ]]; then
      file="${BASH_REMATCH[1]}"
      if is_execution_diff_ignored_path "$story_id" "$file"; then
        skip=1
        continue
      else
        skip=0
      fi
    fi

    if [[ "$skip" == "1" ]]; then
      continue
    fi

    printf '%s\n' "$line"
  done
}

DIFF_FILE="$RUN_DIR/diff.patch"
STAT_FILE="$RUN_DIR/diff.stat"
NAMEONLY_FILE="$RUN_DIR/changed_files.txt"
REVIEW_CHANGED_FILES_FILE="$RUN_DIR/review_changed_files.txt"

TEST_FILE="$RUN_DIR/pytest.txt"
BUNDLE_FILE="$RUN_DIR/review_bundle.md"
REVIEW_PROMPT_FILE="$RUN_DIR/chatgpt_review_prompt.md"
META_FILE="$RUN_DIR/run_meta.txt"
CHECK_ALLOWED_FILES_SCRIPT="$ROOT_DIR/automation/scripts/check_allowed_files.sh"
FALLBACK_CHECK_ALLOWED_FILES_SCRIPT="$RUNNER_DIR/scripts/check_allowed_files.sh"
WORKTREE_TRACKED_LIST_FILE="$RUN_DIR/.worktree_tracked.txt"
WORKTREE_UNTRACKED_LIST_FILE="$RUN_DIR/.worktree_untracked.txt"
WORKTREE_COMPANION_TRACKED_LIST_FILE="$RUN_DIR/.worktree_companion_tracked.txt"
WORKTREE_COMPANION_UNTRACKED_LIST_FILE="$RUN_DIR/.worktree_companion_untracked.txt"

RUN_STATUS="started"
ensure_run_artifact_placeholders
ensure_run_dir_gitignored

cleanup_worktree() {
  if [[ "$WORKTREE_CREATED" == "1" && -n "$WORKTREE_DIR" ]]; then
    git worktree remove --force "$WORKTREE_DIR" >/dev/null 2>&1 || true
    rm -rf "$WORKTREE_DIR" >/dev/null 2>&1 || true
  fi
}

rollback_repository_state() {
  local restore_status=0
  local clean_status=0
  local status_output=""
  local current_head=""
  local story_runs_dir=""
  local -a untracked_paths=()

  info "Run failed before success boundary; restoring clean pre-run repository state"

  current_head="$(git -C "$ROOT_DIR" rev-parse HEAD 2>/dev/null || true)"
  if [[ -z "$ROLLBACK_BASE_HEAD" || "$current_head" != "$ROLLBACK_BASE_HEAD" ]]; then
    echo "ERROR: rollback aborted because current HEAD '$current_head' does not match baseline '$ROLLBACK_BASE_HEAD'" >&2
    return 1
  fi

  git -C "$ROOT_DIR" restore --source="$ROLLBACK_BASE_HEAD" --staged --worktree -- .
  restore_status=$?

  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    [[ "$path" == "$EPHEMERAL_LEDGER_PATH" ]] && continue
    if [[ -n "${RUN_DIR_EXCLUDE_ENTRY:-}" ]]; then
      local run_rel="${RUN_DIR_EXCLUDE_ENTRY#/}"
      run_rel="${run_rel%/}"
      [[ "$path" == "$run_rel" ]] && continue
      [[ "$path" == "$run_rel/"* ]] && continue
    fi
    untracked_paths+=("$path")
  done < <(git -C "$ROOT_DIR" ls-files --others --exclude-standard)

  if (( ${#untracked_paths[@]} > 0 )); then
    git -C "$ROOT_DIR" clean -fdq -- "${untracked_paths[@]}"
    clean_status=$?
  fi

  if [[ -n "$RUN_DIR" ]]; then
    echo "[INFO] preserving run artifacts at: $RUN_DIR (failure debugging enabled)"
    story_runs_dir="$(dirname "$RUN_DIR")"
    rmdir "$story_runs_dir" >/dev/null 2>&1 || true
  fi

  status_output="$(git -C "$ROOT_DIR" status --porcelain -- . "$EPHEMERAL_LEDGER_EXCLUDE_PATHSPEC" || true)"

  if [[ "$restore_status" -ne 0 || "$clean_status" -ne 0 || -n "$status_output" ]]; then
    echo "ERROR: automatic rollback failed" >&2
    if [[ "$restore_status" -ne 0 ]]; then
      echo "ERROR: tracked restore failed with exit code $restore_status" >&2
    fi
    if [[ "$clean_status" -ne 0 ]]; then
      echo "ERROR: untracked cleanup failed with exit code $clean_status" >&2
    fi
    if [[ -n "$status_output" ]]; then
      echo "ERROR: repository remains dirty after rollback:" >&2
      printf '%s\n' "$status_output" >&2
    fi
    return 1
  fi

  info "Rollback restored repository to the clean pre-run state"
}

handle_exit() {
  local exit_code="$1"
  local final_exit_code="$exit_code"

  set +e
  if [[ "$final_exit_code" -eq 0 ]]; then
    RUN_STATUS="success"
  elif [[ "$RUN_STATUS" != "failed" ]]; then
    RUN_STATUS="failed"
  fi
  write_run_meta

  if [[ "$ROLLBACK_ARMED" == "1" ]]; then
    rollback_repository_state
    if [[ $? -ne 0 ]]; then
      final_exit_code=1
      RUN_STATUS="failed"
    elif [[ "$exit_code" -eq 0 ]]; then
      final_exit_code=1
      RUN_STATUS="failed"
    fi
    write_run_meta
  fi

  restore_ephemeral_story_change_ledger
  cleanup_worktree
  trap - EXIT INT TERM
  exit "$final_exit_code"
}

trap 'handle_exit $?' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

setup_isolated_worktree() {
  WORKTREE_HEAD="$(git rev-parse HEAD)"
  WORKTREE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/zumbot-codex-worktree-XXXXXX")"
  git worktree add --detach "$WORKTREE_DIR" "$WORKTREE_HEAD" >/dev/null
  WORKTREE_CREATED="1"
  write_run_meta
}

if story_is_code_only_for_execution_filter "$STORY_ID"; then
  EXECUTION_COMPANION_FILTER_MODE="enabled"
else
  EXECUTION_COMPANION_FILTER_MODE="disabled"
fi
write_run_meta

generate_repository_map_runtime "$REPOSITORY_MAP_RUNTIME_FILE" "$STORY_ID"
REPOSITORY_MAP_INJECTION_STATUS="injected"
write_run_meta

generate_story_context "$STORY_ID" "$STORY_CONTEXT_FILE" "$CONTEXT_MODE" "$REPOSITORY_MAP_RUNTIME_REL"
build_codex_prompt "$CODEX_PROMPT_FILE" "$REPOSITORY_MAP_RUNTIME_REL"
CONTEXT_FILES_CSV="$(printf '%s,' "${GENERATED_CONTEXT_FILES[@]}")"
CONTEXT_FILES_CSV="${CONTEXT_FILES_CSV%,}"
write_run_meta

setup_isolated_worktree

info "Zumbot Codex pipeline starting"
info "Repo root: $ROOT_DIR"
info "Branch: $BRANCH_NAME"
info "HEAD: $CURRENT_HEAD"
info "Story id: $STORY_ID"
info "Prompt file: $PROMPT_FILE"
info "Repository map artifact: $REPOSITORY_MAP_RUNTIME_FILE"
info "Context mode: $CONTEXT_MODE"
info "Isolated worktree: $WORKTREE_DIR"
if [[ ${#GENERATED_CONTEXT_FILES[@]} -gt 0 ]]; then
  info "Context files: ${GENERATED_CONTEXT_FILES[*]}"
else
  info "Context files: none"
fi
info "Run dir: $RUN_DIR"

run_codex() {
  local -a cmd
  cmd=(codex exec --full-auto -C "$WORKTREE_DIR" -o "$LAST_MESSAGE_FILE")

  if [[ -n "$CODEX_MODEL" ]]; then
    cmd+=(-m "$CODEX_MODEL")
  fi

  if [[ -n "$CODEX_EXTRA_ARGS" ]]; then
    # shellcheck disable=SC2206
    local extra=( $CODEX_EXTRA_ARGS )
    cmd+=("${extra[@]}")
  fi

  cmd+=(-)

  info "Running Codex"
  printf '[INFO] Command:' >&2
  printf ' %q' "${cmd[@]}" >&2
  printf '\n' >&2

  set +e
  "${cmd[@]}" < "$CODEX_PROMPT_FILE" > "$LOG_FILE" 2>&1
  local exit_code=$?
  set -e

  echo "$exit_code"
}



run_pytest() {
  if [[ "$SKIP_PYTEST" == "1" ]]; then
    echo "SKIPPED"
    return 0
  fi

  set +e
  if [[ -n "$PYTEST_TARGET" ]]; then
    info "Running pytest target: $PYTEST_TARGET"
    pytest $PYTEST_TARGET >"$TEST_FILE" 2>&1
  else
    info "Running pytest"
    pytest >"$TEST_FILE" 2>&1
  fi
  local exit_code=$?
  set -e

  echo "$exit_code"
}

filter_materialization_exclusions() {
  local tmp_file

  tmp_file="$(mktemp)"
  grep -vx "$EPHEMERAL_LEDGER_PATH" "$WORKTREE_TRACKED_LIST_FILE" > "$tmp_file" || true
  mv "$tmp_file" "$WORKTREE_TRACKED_LIST_FILE"

  tmp_file="$(mktemp)"
  grep -vx "$EPHEMERAL_LEDGER_PATH" "$WORKTREE_UNTRACKED_LIST_FILE" > "$tmp_file" || true
  mv "$tmp_file" "$WORKTREE_UNTRACKED_LIST_FILE"
}

isolate_explicit_execution_companion_paths() {
  local rel tmp_file

  : > "$WORKTREE_COMPANION_TRACKED_LIST_FILE"
  : > "$WORKTREE_COMPANION_UNTRACKED_LIST_FILE"

  tmp_file="$(mktemp)"
  while IFS= read -r rel; do
    [[ -n "$rel" ]] || continue
    if is_execution_companion_artifact_path "$STORY_ID" "$rel"; then
      printf '%s\n' "$rel" >> "$WORKTREE_COMPANION_TRACKED_LIST_FILE"
      COMPANION_CONTAMINATION_DETECTED="1"
      continue
    fi
    printf '%s\n' "$rel" >> "$tmp_file"
  done < "$WORKTREE_TRACKED_LIST_FILE"
  mv "$tmp_file" "$WORKTREE_TRACKED_LIST_FILE"

  tmp_file="$(mktemp)"
  while IFS= read -r rel; do
    [[ -n "$rel" ]] || continue
    if is_execution_companion_artifact_path "$STORY_ID" "$rel"; then
      printf '%s\n' "$rel" >> "$WORKTREE_COMPANION_UNTRACKED_LIST_FILE"
      COMPANION_CONTAMINATION_DETECTED="1"
      continue
    fi
    printf '%s\n' "$rel" >> "$tmp_file"
  done < "$WORKTREE_UNTRACKED_LIST_FILE"
  mv "$tmp_file" "$WORKTREE_UNTRACKED_LIST_FILE"
}

load_worktree_changes() {
  git -C "$WORKTREE_DIR" diff --name-only "$WORKTREE_HEAD" -- > "$WORKTREE_TRACKED_LIST_FILE" || true
  git -C "$WORKTREE_DIR" ls-files --others --exclude-standard > "$WORKTREE_UNTRACKED_LIST_FILE" || true

  filter_materialization_exclusions
  isolate_explicit_execution_companion_paths

  MATERIALIZED_TRACKED_COUNT="$(wc -l < "$WORKTREE_TRACKED_LIST_FILE" | tr -d ' ')"
  MATERIALIZED_UNTRACKED_COUNT="$(wc -l < "$WORKTREE_UNTRACKED_LIST_FILE" | tr -d ' ')"
  MATERIALIZED_CHANGE_COUNT="$(( MATERIALIZED_TRACKED_COUNT + MATERIALIZED_UNTRACKED_COUNT ))"

  if [[ "$COMPANION_CONTAMINATION_DETECTED" == "1" && "$MATERIALIZED_CHANGE_COUNT" -eq 0 ]]; then
    fail "explicit companion contamination removed all implementation changes; refusing empty delivery surface"
  fi

  write_run_meta
}

materialize_tracked_changes() {
  local rel patch_file

  if [[ "$MATERIALIZED_TRACKED_COUNT" == "0" ]]; then
    return 0
  fi

  patch_file="$(mktemp)"

  while IFS= read -r rel; do
    [[ -n "$rel" ]] || continue
    git -C "$WORKTREE_DIR" diff --binary "$WORKTREE_HEAD" -- "$rel" >> "$patch_file"
  done < "$WORKTREE_TRACKED_LIST_FILE"

  if [[ -s "$patch_file" ]]; then
    git -C "$ROOT_DIR" apply --binary --whitespace=nowarn < "$patch_file"
  fi

  rm -f "$patch_file"
}

materialize_untracked_files() {
  local rel src dest

  while IFS= read -r rel; do
    [[ -n "$rel" ]] || continue
    src="$WORKTREE_DIR/$rel"
    dest="$ROOT_DIR/$rel"

    [[ -f "$src" ]] || fail "unsupported untracked worktree path (not a regular file): $rel"

    mkdir -p "$(dirname "$dest")"
    cp "$src" "$dest"
  done < "$WORKTREE_UNTRACKED_LIST_FILE"
}

verify_materialized_changes() {
  local rel worktree_path primary_path

  while IFS= read -r rel; do
    [[ -n "$rel" ]] || continue
    worktree_path="$WORKTREE_DIR/$rel"
    primary_path="$ROOT_DIR/$rel"

    if [[ -e "$worktree_path" ]]; then
      [[ -e "$primary_path" ]] || fail "materialization missing tracked path in primary checkout: $rel"
      cmp -s "$worktree_path" "$primary_path" || fail "materialized tracked path does not match isolated worktree output: $rel"
    else
      [[ ! -e "$primary_path" ]] || fail "materialized tracked deletion did not reach primary checkout: $rel"
    fi
  done < "$WORKTREE_TRACKED_LIST_FILE"

  while IFS= read -r rel; do
    [[ -n "$rel" ]] || continue
    worktree_path="$WORKTREE_DIR/$rel"
    primary_path="$ROOT_DIR/$rel"

    [[ -e "$primary_path" ]] || fail "materialization missing untracked path in primary checkout: $rel"
    cmp -s "$worktree_path" "$primary_path" || fail "materialized untracked path does not match isolated worktree output: $rel"
  done < "$WORKTREE_UNTRACKED_LIST_FILE"
}

materialize_worktree_changes() {
  load_worktree_changes

  if [[ "$MATERIALIZED_CHANGE_COUNT" -eq 0 ]]; then
    MATERIALIZATION_STATUS="not_needed"
    write_run_meta
    return 0
  fi

  MATERIALIZATION_STATUS="in_progress"
  write_run_meta

  info "Materializing isolated worktree changes into primary checkout"


  materialize_tracked_changes
  materialize_untracked_files
  verify_materialized_changes

  MATERIALIZATION_STATUS="applied"
  write_run_meta
}

append_untracked_artifacts() {
  local rel

  if [[ "$MATERIALIZED_UNTRACKED_COUNT" == "0" ]]; then
    return 0
  fi

  {
    echo
    echo "Untracked files materialized into primary checkout:"
    while IFS= read -r rel; do
      [[ -n "$rel" ]] || continue
      echo "  $rel"
    done < "$WORKTREE_UNTRACKED_LIST_FILE"
  } >> "$STAT_FILE"
}

write_review_diff_patch() {
  local merge_base="$1"
  local temp_index=""
  local git_index_path=""

  if [[ "$MATERIALIZED_UNTRACKED_COUNT" == "0" ]]; then
    git diff "$merge_base" -- . "$EPHEMERAL_LEDGER_EXCLUDE_PATHSPEC" \
      | filter_ignored_execution_diff_paths "$STORY_ID" > "$DIFF_FILE" || true
    return 0
  fi

  temp_index="$(mktemp)"
  git_index_path="$(git -C "$ROOT_DIR" rev-parse --git-path index)"

  if [[ -f "$git_index_path" ]]; then
    cp "$git_index_path" "$temp_index"
  else
    : > "$temp_index"
  fi

  GIT_INDEX_FILE="$temp_index" git -C "$ROOT_DIR" add -N \
    --pathspec-from-file="$WORKTREE_UNTRACKED_LIST_FILE" -- >/dev/null

  GIT_INDEX_FILE="$temp_index" git -C "$ROOT_DIR" diff "$merge_base" -- . "$EPHEMERAL_LEDGER_EXCLUDE_PATHSPEC" \
    | filter_ignored_execution_diff_paths "$STORY_ID" > "$DIFF_FILE" || true

  rm -f "$temp_index"
}

write_review_diff_stat() {
  if [[ ! -s "$DIFF_FILE" ]]; then
    : > "$STAT_FILE"
    return 0
  fi

  git apply --stat < "$DIFF_FILE" > "$STAT_FILE" || true
}

is_canonical_active_story_bundle_artifact() {
  local rel_path="$1"

  [[ -n "$STORY_ID" && "$STORY_ID" != "ADHOC" ]] || return 1

  if [[ "$rel_path" == "automation/bundle_packs/$STORY_ID.bundle.md" ]]; then
    return 0
  fi

  if [[ "$rel_path" == "automation/bundles/active/$STORY_ID/"* ]]; then
    return 0
  fi

  return 1
}

is_committed_same_story_bundle_artifact() {
  local rel_path="$1"

  is_canonical_active_story_bundle_artifact "$rel_path" || return 1
  git cat-file -e "HEAD:$rel_path" >/dev/null 2>&1 || return 1
  git diff --quiet HEAD -- "$rel_path"
}

collect_git_artifacts() {
  local merge_base
  merge_base="$(git merge-base "$REVIEW_BASE_REF" HEAD)"
  REVIEW_ARTIFACT_BASE="$merge_base"

  tracked_names_file="$RUN_DIR/.tracked_names.txt"
  untracked_names_file="$RUN_DIR/.untracked_names.txt"

  info "Collecting git artifacts"

  write_review_diff_patch "$merge_base"
  write_review_diff_stat

  git diff --name-only "$merge_base" -- . "$EPHEMERAL_LEDGER_EXCLUDE_PATHSPEC" > "$tracked_names_file" || true
  cp "$WORKTREE_UNTRACKED_LIST_FILE" "$untracked_names_file"

  {
    if [[ -f "$tracked_names_file" ]]; then
      cat "$tracked_names_file"
    fi
    if [[ -f "$untracked_names_file" ]]; then
      cat "$untracked_names_file"
    fi
  } | sed '/^$/d' | LC_ALL=C sort -u > "$NAMEONLY_FILE"

  {
    if [[ -f "$tracked_names_file" ]]; then
      while IFS= read -r changed_file; do
        [[ -n "$changed_file" ]] || continue
        if is_execution_companion_artifact_path "$STORY_ID" "$changed_file"; then
          continue
        fi
        printf '%s\n' "$changed_file"
      done < "$tracked_names_file"
    fi
    if [[ -f "$untracked_names_file" ]]; then
      while IFS= read -r changed_file; do
        [[ -n "$changed_file" ]] || continue
        if is_execution_companion_artifact_path "$STORY_ID" "$changed_file"; then
          continue
        fi
        printf '%s\n' "$changed_file"
      done < "$untracked_names_file"
    fi
  } | sed '/^$/d' | LC_ALL=C sort -u > "$REVIEW_CHANGED_FILES_FILE"

  append_untracked_artifacts
}

check_allowed_files() {
  local bundle_dir scope_file script_path changed_file filtered_nameonly_file
  bundle_dir="$ROOT_DIR/automation/bundles/active/$STORY_ID"
  scope_file="$bundle_dir/02_file_scope.md"
  script_path="$CHECK_ALLOWED_FILES_SCRIPT"

  if [[ ! -f "$script_path" && -f "$FALLBACK_CHECK_ALLOWED_FILES_SCRIPT" ]]; then
    script_path="$FALLBACK_CHECK_ALLOWED_FILES_SCRIPT"
  fi

  if [[ ! -f "$scope_file" ]]; then
    SCOPE_PARSE_STATUS="missing"
    FILES_NOT_ALLOWED_PARSE_STATUS="missing"
    write_run_meta
    echo "ERROR: scope file is missing: $scope_file" >&2
    exit 1
  fi

  if ! grep -q '^## Files Allowed To Change$' "$scope_file"; then
    SCOPE_PARSE_STATUS="unparseable"
    write_run_meta
    echo "ERROR: scope file is unparseable: $scope_file" >&2
    exit 1
  fi

  if grep -q '^## Files Not Allowed To Change$' "$scope_file"; then
    FILES_NOT_ALLOWED_PARSE_STATUS="parsed"
  else
    FILES_NOT_ALLOWED_PARSE_STATUS="unavailable"
  fi

  if [[ -n "${tracked_names_file:-}" || -n "${untracked_names_file:-}" ]]; then
    : > "$NAMEONLY_FILE"
    filtered_nameonly_file="$RUN_DIR/.changed_files.filtered.txt"
    : > "$filtered_nameonly_file"

    if [[ -n "${tracked_names_file:-}" && -f "$tracked_names_file" ]]; then
      while IFS= read -r changed_file; do
        [[ -n "$changed_file" ]] || continue
        if is_committed_same_story_bundle_artifact "$changed_file" \
          || is_execution_companion_artifact_path "$STORY_ID" "$changed_file"; then
          if is_execution_companion_artifact_path "$STORY_ID" "$changed_file"; then
            COMPANION_CONTAMINATION_DETECTED="1"
          fi
          continue
        fi
        printf '%s\n' "$changed_file" >> "$filtered_nameonly_file"
      done < "$tracked_names_file"
    fi

    if [[ -n "${untracked_names_file:-}" && -f "$untracked_names_file" ]]; then
      while IFS= read -r changed_file; do
        [[ -n "$changed_file" ]] || continue
        if is_execution_companion_artifact_path "$STORY_ID" "$changed_file"; then
          COMPANION_CONTAMINATION_DETECTED="1"
          continue
        fi
        printf '%s\n' "$changed_file" >> "$filtered_nameonly_file"
      done < "$untracked_names_file"
    fi

    if [[ -s "$filtered_nameonly_file" ]]; then
      LC_ALL=C sort -u "$filtered_nameonly_file" > "$NAMEONLY_FILE"
    fi

    if [[ "$COMPANION_CONTAMINATION_DETECTED" == "1" && ! -s "$NAMEONLY_FILE" ]]; then
      fail "explicit companion contamination removed all implementation changes; refusing empty delivery surface"
    fi
  fi

  info "Validating changed files against bundle scope"
  if bash "$script_path" "$STORY_ID" "$NAMEONLY_FILE" "$bundle_dir" >&2; then
    SCOPE_PARSE_STATUS="parsed"
    write_run_meta
  else
    local exit_code=$?
    if [[ "$SCOPE_PARSE_STATUS" != "missing" && "$SCOPE_PARSE_STATUS" != "unparseable" ]]; then
      SCOPE_PARSE_STATUS="parsed"
    fi
    write_run_meta
    return "$exit_code"
  fi

  rm -f "$tracked_names_file" "$untracked_names_file"
}

CODEX_EXIT="$(run_codex)"
write_run_meta

materialize_worktree_changes
collect_git_artifacts
write_run_meta

check_allowed_files

if [[ "$SKIP_PYTEST" == "1" ]]; then
  PYTEST_EXIT="SKIPPED"
  echo "pytest skipped by SKIP_PYTEST=1" > "$TEST_FILE"
else
  PYTEST_EXIT="$(run_pytest)"
fi
write_run_meta

CHANGED_FILES="$(cat "$NAMEONLY_FILE" 2>/dev/null || true)"
REVIEW_CHANGED_FILES_CONTENT="$(cat "$REVIEW_CHANGED_FILES_FILE" 2>/dev/null || true)"
DIFF_STAT_CONTENT="$(cat "$STAT_FILE" 2>/dev/null || true)"
PYTEST_OUTPUT_CONTENT="$(cat "$TEST_FILE" 2>/dev/null || true)"
LAST_MESSAGE_CONTENT="$(cat "$LAST_MESSAGE_FILE" 2>/dev/null || true)"

cat > "$MANIFEST_FILE" <<MANIFEST
# Codex Run Manifest

- story_id: $STORY_ID
- prompt_file: $PROMPT_FILE
- branch: $BRANCH_NAME
- starting_head: $CURRENT_HEAD
- review_base_ref: $REVIEW_BASE_REF
- review_diff_range: $REVIEW_DIFF_RANGE
- review_artifact_base: $REVIEW_ARTIFACT_BASE
- execution_companion_filter_mode: $EXECUTION_COMPANION_FILTER_MODE
- run_timestamp_utc: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
- run_dir: $RUN_DIR
- context_mode: $CONTEXT_MODE
- repository_map_runtime_file: $REPOSITORY_MAP_RUNTIME_FILE
- repository_map_injection_status: $REPOSITORY_MAP_INJECTION_STATUS
- repository_map_source_docs: ${REPOSITORY_MAP_SOURCE_DOCS:-none}
- isolated_run: yes
- isolated_worktree_dir: $WORKTREE_DIR
- isolated_worktree_head: $WORKTREE_HEAD
- isolated_worktree_cleanup: exit_trap
- materialization_status: $MATERIALIZATION_STATUS
- materialized_tracked_changes: $MATERIALIZED_TRACKED_COUNT
- materialized_untracked_files: $MATERIALIZED_UNTRACKED_COUNT
- codex_exit_code: $CODEX_EXIT
- pytest_exit_code: $PYTEST_EXIT
- pytest_command: ${PYTEST_TARGET:+pytest $PYTEST_TARGET}${PYTEST_TARGET:+" "}${PYTEST_TARGET:-pytest}
- changed_files_detected: $( [[ -n "$CHANGED_FILES" ]] && echo "yes" || echo "no" )

## Included Story Context Files
$(if [[ ${#GENERATED_CONTEXT_FILES[@]} -gt 0 ]]; then
    for rel in "${GENERATED_CONTEXT_FILES[@]}"; do
      printf -- "- %s\n" "$rel"
    done
  else
    printf -- "- none\n"
  fi)

## Artifacts
- manifest.md
- repository_map_runtime.md
- story_context.md
- codex_prompt.md
- codex_last_message.txt
- codex.log
- diff.patch
- diff.stat
- changed_files.txt
- review_changed_files.txt
- pytest.txt
- review_bundle.md
- chatgpt_review_prompt.md
- run_meta.txt
MANIFEST

cat > "$BUNDLE_FILE" <<REVIEW
# Codex Review Bundle

## Story ID
$STORY_ID

## Prompt File
$PROMPT_FILE

## Branch
$BRANCH_NAME

## Starting HEAD
$CURRENT_HEAD

## Review Diff Source
$REVIEW_DIFF_RANGE (merge-base $REVIEW_ARTIFACT_BASE)

## Changed Files (origin/main...HEAD)
\`\`\`
$REVIEW_CHANGED_FILES_CONTENT
\`\`\`

## Scope-Validated Delivery Surface
\`\`\`
$CHANGED_FILES
\`\`\`

## Diff Stat
\`\`\`
$DIFF_STAT_CONTENT
\`\`\`

## Pytest Output
\`\`\`
$PYTEST_OUTPUT_CONTENT
\`\`\`

## Codex Last Message
\`\`\`
$LAST_MESSAGE_CONTENT
\`\`\`

## Artifacts Directory
$RUN_DIR
REVIEW

cat > "$REVIEW_PROMPT_FILE" <<PROMPT
Review this Zumbot Codex change.

Context:
- Story ID: $STORY_ID
- Prompt file: $PROMPT_FILE
- Branch: $BRANCH_NAME
- Starting HEAD: $CURRENT_HEAD
- Review diff source: $REVIEW_DIFF_RANGE
- Review artifact base: $REVIEW_ARTIFACT_BASE

Please review:
1. architecture fit
2. scope creep
3. safety issues
4. hallucination risk
5. missing tests
6. missing docs
7. branch/workflow compliance

Use these artifacts from:
$RUN_DIR

Changed files (origin/main...HEAD):
$REVIEW_CHANGED_FILES_CONTENT

Scope-validated delivery surface:
$CHANGED_FILES

Diff stat:
$DIFF_STAT_CONTENT

Pytest:
$PYTEST_OUTPUT_CONTENT

## Required output format

Return only a markdown document in exactly this structure.

Do not include:
- any preamble
- any narration
- any explanation before the first heading
- any tool commentary
- any surrounding code fences

The first non-empty line must be exactly:

# AI Review

After the findings section, include exactly:

# AI Review Result

Under # AI Review Result, output exactly one of:
- PASS
- FAIL

Required shape:

# AI Review

## Findings by severity
- <finding 1>
- <finding 2>

## Requested areas summary
- Architecture fit: <text>
- Scope creep: <text>
- Safety issues: <text>
- Hallucination risk: <text>
- Missing tests: <text>
- Missing docs: <text>
- Branch/workflow compliance: <text>

# AI Review Result

PASS

If there are blocking issues, output FAIL instead of PASS.

Do not repeat the prompt.
Do not echo the supplied context.
Do not output anything before # AI Review.
PROMPT

RUN_STATUS="failed"
write_run_meta
info "Artifacts generated in: $RUN_DIR"

if [[ "$CODEX_EXIT" != "0" ]]; then
  echo "ERROR: Codex finished with non-zero exit code: $CODEX_EXIT" >&2
  exit "$CODEX_EXIT"
fi

if [[ "$PYTEST_EXIT" != "0" && "$PYTEST_EXIT" != "SKIPPED" ]]; then
  echo "ERROR: pytest finished with non-zero exit code: $PYTEST_EXIT" >&2
  exit "$PYTEST_EXIT"
fi

RUN_STATUS="success"
write_run_meta
ROLLBACK_ARMED="0"
info "Done"
