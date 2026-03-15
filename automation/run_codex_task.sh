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

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

info() {
  echo "[INFO] $*" >&2
}

warn() {
  echo "[WARN] $*" >&2
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
    function normalize(value) {
      value = tolower(value)
      gsub(/`/, "", value)
      gsub(/^[[:space:]]+/, "", value)
      gsub(/[[:space:]]+$/, "", value)
      return value
    }

    function is_target_heading(line, kind, normalized) {
      normalized = normalize(line)
      sub(/^##[[:space:]]+/, "", normalized)

      if (kind == "allowed") {
        if (normalized == "files allowed to change") return 1
        if (normalized == "files allowed to change:") return 1
        if (normalized == "allowed files") return 1
        if (normalized ~ /^allowed files for future /) return 1
        return 0
      }

      if (kind == "blocked") {
        if (normalized == "files not allowed to change") return 1
        if (normalized == "files explicitly not allowed to change") return 1
        if (normalized == "forbidden files/areas for future us-pay-2 implementation") return 1
        if (normalized == "files/layers that must not be changed") return 1
        if (normalized == "forbidden files/areas") return 1
        if (normalized == "forbidden files") return 1
        return 0
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

emit_scope_list_with_status() {
  local status="$1"
  shift || true

  if [[ "$status" == "parsed" ]]; then
    if [[ $# -gt 0 ]]; then
      emit_markdown_list_or_none "$@"
    else
      emit_markdown_list_or_none
    fi
  else
    echo "  unavailable"
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

      if [[ ${#allowed_files[@]} -gt 0 && ${#blocked_files[@]} -gt 0 ]]; then
        scope_parse_status="parsed"
      else
        scope_parse_status="unparseable"
      fi
    elif [[ -d "$bundle_dir" ]]; then
      scope_parse_status="missing"
    fi
  fi

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
    if [[ "$scope_parse_status" == "parsed" ]]; then
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
GIT_STATUS="$(git status --porcelain)"
PROMPT_CONTENT="$(cat "$PROMPT_FILE")"

[[ "$BRANCH_NAME" != "main" ]] || fail "do not run automation on main; switch to a feature branch first"
[[ -z "$GIT_STATUS" ]] || fail "working tree is not clean; commit/stash changes first"
[[ -n "$PROMPT_CONTENT" ]] || fail "prompt file is empty: $PROMPT_FILE"

SKIP_PYTEST="${SKIP_PYTEST:-0}"
PYTEST_TARGET="${PYTEST_TARGET:-}"
CODEX_MODEL="${CODEX_MODEL:-}"
CODEX_EXTRA_ARGS="${CODEX_EXTRA_ARGS:-}"

STORY_ID="$(derive_story_id "$PROMPT_FILE")"
RUN_ID="$(date -u +"%Y-%m-%d_%H-%M-%S")"
RUN_DIR="$RUNS_ROOT/$STORY_ID/$RUN_ID"
WORKTREE_DIR=""
WORKTREE_HEAD=""
WORKTREE_CREATED="0"

mkdir -p "$RUN_DIR"

MANIFEST_FILE="$RUN_DIR/manifest.md"
STORY_CONTEXT_FILE="$RUN_DIR/story_context.md"
CODEX_PROMPT_FILE="$RUN_DIR/codex_prompt.md"
REPOSITORY_MAP_RUNTIME_FILE="$RUN_DIR/repository_map_runtime.md"
LOG_FILE="$RUN_DIR/codex.log"
LAST_MESSAGE_FILE="$RUN_DIR/codex_last_message.txt"
DIFF_FILE="$RUN_DIR/diff.patch"
STAT_FILE="$RUN_DIR/diff.stat"
NAMEONLY_FILE="$RUN_DIR/changed_files.txt"
TEST_FILE="$RUN_DIR/pytest.txt"
BUNDLE_FILE="$RUN_DIR/review_bundle.md"
REVIEW_PROMPT_FILE="$RUN_DIR/chatgpt_review_prompt.md"
META_FILE="$RUN_DIR/run_meta.txt"
CHECK_ALLOWED_FILES_SCRIPT="$ROOT_DIR/automation/scripts/check_allowed_files.sh"
FALLBACK_CHECK_ALLOWED_FILES_SCRIPT="$RUNNER_DIR/scripts/check_allowed_files.sh"
WORKTREE_TRACKED_LIST_FILE="$RUN_DIR/.worktree_tracked.txt"
WORKTREE_UNTRACKED_LIST_FILE="$RUN_DIR/.worktree_untracked.txt"
MATERIALIZATION_STATUS="not_needed"
MATERIALIZED_TRACKED_COUNT="0"
MATERIALIZED_UNTRACKED_COUNT="0"
MATERIALIZED_CHANGE_COUNT="0"
REVIEW_ARTIFACT_BASE=""
REPOSITORY_MAP_RUNTIME_REL="repository_map_runtime.md"
REPOSITORY_MAP_INJECTION_STATUS="pending"
REPOSITORY_MAP_SOURCE_DOCS=""

cleanup_worktree() {
  local exit_code=$?
  if [[ "$WORKTREE_CREATED" == "1" && -n "$WORKTREE_DIR" ]]; then
    git worktree remove --force "$WORKTREE_DIR" >/dev/null 2>&1 || true
    rm -rf "$WORKTREE_DIR" >/dev/null 2>&1 || true
  fi
  return "$exit_code"
}

trap cleanup_worktree EXIT

setup_isolated_worktree() {
  WORKTREE_HEAD="$(git rev-parse HEAD)"
  WORKTREE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/zumbot-codex-worktree-XXXXXX")"
  git worktree add --detach "$WORKTREE_DIR" "$WORKTREE_HEAD" >/dev/null
  WORKTREE_CREATED="1"
}

generate_repository_map_runtime "$REPOSITORY_MAP_RUNTIME_FILE" "$STORY_ID"
REPOSITORY_MAP_INJECTION_STATUS="injected"
generate_story_context "$STORY_ID" "$STORY_CONTEXT_FILE" "$CONTEXT_MODE" "$REPOSITORY_MAP_RUNTIME_REL"
build_codex_prompt "$CODEX_PROMPT_FILE" "$REPOSITORY_MAP_RUNTIME_REL"
CONTEXT_FILES_CSV="$(printf '%s,' "${GENERATED_CONTEXT_FILES[@]}")"
CONTEXT_FILES_CSV="${CONTEXT_FILES_CSV%,}"
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

cat > "$META_FILE" <<META
story_id=$STORY_ID
branch=$BRANCH_NAME
head=$CURRENT_HEAD
review_base_ref=$REVIEW_BASE_REF
review_diff_range=$REVIEW_DIFF_RANGE
prompt_file=$PROMPT_FILE
run_dir=$RUN_DIR
timestamp_utc=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
context_mode=$CONTEXT_MODE
context_files=$CONTEXT_FILES_CSV
repository_map_runtime_file=$REPOSITORY_MAP_RUNTIME_FILE
repository_map_injection_status=$REPOSITORY_MAP_INJECTION_STATUS
repository_map_source_docs=$REPOSITORY_MAP_SOURCE_DOCS
skip_pytest=$SKIP_PYTEST
pytest_target=$PYTEST_TARGET
codex_model=$CODEX_MODEL
isolated_run=true
isolated_worktree_dir=$WORKTREE_DIR
isolated_worktree_head=$WORKTREE_HEAD
isolated_worktree_cleanup=exit_trap
META

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
    python3 -m pytest $PYTEST_TARGET >"$TEST_FILE" 2>&1
  else
    info "Running pytest"
    python3 -m pytest >"$TEST_FILE" 2>&1
  fi
  local exit_code=$?
  set -e

  echo "$exit_code"
}

load_worktree_changes() {
  git -C "$WORKTREE_DIR" diff --name-only "$WORKTREE_HEAD" -- > "$WORKTREE_TRACKED_LIST_FILE" || true
  git -C "$WORKTREE_DIR" ls-files --others --exclude-standard > "$WORKTREE_UNTRACKED_LIST_FILE" || true

  MATERIALIZED_TRACKED_COUNT="$(wc -l < "$WORKTREE_TRACKED_LIST_FILE" | tr -d ' ')"
  MATERIALIZED_UNTRACKED_COUNT="$(wc -l < "$WORKTREE_UNTRACKED_LIST_FILE" | tr -d ' ')"
}

materialize_tracked_changes() {
  if [[ "$MATERIALIZED_TRACKED_COUNT" == "0" ]]; then
    return 0
  fi

  git -C "$WORKTREE_DIR" diff --binary "$WORKTREE_HEAD" -- | git -C "$ROOT_DIR" apply --binary --whitespace=nowarn
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

  MATERIALIZED_CHANGE_COUNT="$(( MATERIALIZED_TRACKED_COUNT + MATERIALIZED_UNTRACKED_COUNT ))"

  if [[ "$MATERIALIZED_CHANGE_COUNT" -eq 0 ]]; then
    MATERIALIZATION_STATUS="not_needed"
    return 0
  fi

  MATERIALIZATION_STATUS="in_progress"
  info "Materializing isolated worktree changes into primary checkout"
  materialize_tracked_changes
  materialize_untracked_files
  verify_materialized_changes
  MATERIALIZATION_STATUS="applied"
}

append_untracked_artifacts() {
  local rel file

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

  while IFS= read -r rel; do
    [[ -n "$rel" ]] || continue
    file="$ROOT_DIR/$rel"
    printf '\n' >> "$DIFF_FILE"
    git diff --no-index -- /dev/null "$file" >> "$DIFF_FILE" || true
  done < "$WORKTREE_UNTRACKED_LIST_FILE"
}

collect_git_artifacts() {
  local merge_base tracked_names_file untracked_names_file
  merge_base="$(git merge-base "$REVIEW_BASE_REF" HEAD)"
  REVIEW_ARTIFACT_BASE="$merge_base"
  tracked_names_file="$RUN_DIR/.tracked_names.txt"
  untracked_names_file="$RUN_DIR/.untracked_names.txt"

  info "Collecting git artifacts"
  git diff --stat "$merge_base" -- > "$STAT_FILE" || true
  git diff "$merge_base" -- > "$DIFF_FILE" || true
  git diff --name-only "$merge_base" -- > "$tracked_names_file" || true
  cp "$WORKTREE_UNTRACKED_LIST_FILE" "$untracked_names_file"
  cat "$tracked_names_file" "$untracked_names_file" | sed '/^$/d' | sort -u > "$NAMEONLY_FILE"
  append_untracked_artifacts
  rm -f "$tracked_names_file" "$untracked_names_file"
}

check_allowed_files() {
  local bundle_dir scope_file script_path
  bundle_dir="$ROOT_DIR/automation/bundles/active/$STORY_ID"
  scope_file="$bundle_dir/02_file_scope.md"
  script_path="$CHECK_ALLOWED_FILES_SCRIPT"

  if [[ ! -f "$script_path" && -f "$FALLBACK_CHECK_ALLOWED_FILES_SCRIPT" ]]; then
    script_path="$FALLBACK_CHECK_ALLOWED_FILES_SCRIPT"
  fi

  if [[ ! -f "$scope_file" ]]; then
    echo "ERROR: scope file is missing: $scope_file" >&2
    exit 1
  fi

  info "Validating changed files against bundle scope"
  bash "$script_path" "$STORY_ID" "$NAMEONLY_FILE" "$bundle_dir"
}

CODEX_EXIT="$(run_codex)"
materialize_worktree_changes

collect_git_artifacts
check_allowed_files

if [[ "$SKIP_PYTEST" == "1" ]]; then
  PYTEST_EXIT="SKIPPED"
  echo "pytest skipped by SKIP_PYTEST=1" > "$TEST_FILE"
else
  PYTEST_EXIT="$(run_pytest)"
fi

CHANGED_FILES="$(cat "$NAMEONLY_FILE" 2>/dev/null || true)"
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
- pytest_command: ${PYTEST_TARGET:+python3 -m pytest $PYTEST_TARGET}${PYTEST_TARGET:+" "}${PYTEST_TARGET:-python3 -m pytest}
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

## Changed Files
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

Changed files:
$CHANGED_FILES

Diff stat:
$DIFF_STAT_CONTENT

Pytest:
$PYTEST_OUTPUT_CONTENT
PROMPT

info "Artifacts generated in: $RUN_DIR"
info "Done"

if [[ "$CODEX_EXIT" != "0" ]]; then
  echo "ERROR: Codex finished with non-zero exit code: $CODEX_EXIT" >&2
  exit "$CODEX_EXIT"
fi

if [[ "$PYTEST_EXIT" != "0" && "$PYTEST_EXIT" != "SKIPPED" ]]; then
  echo "ERROR: pytest finished with non-zero exit code: $PYTEST_EXIT" >&2
  exit "$PYTEST_EXIT"
fi
