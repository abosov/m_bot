#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)"
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

generate_story_context() {
  local story_id="$1"
  local out_file="$2"
  local mode="$3"
  local bundle_dir="$ROOT_DIR/automation/bundles/active/$story_id"
  GENERATED_CONTEXT_FILES=()

  if [[ ! -d "$bundle_dir" ]]; then
    cat > "$out_file" <<CTX
# Story Context

No active story bundle found for story id: $story_id

Requested context mode: $mode

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
LOG_FILE="$RUN_DIR/codex.log"
LAST_MESSAGE_FILE="$RUN_DIR/codex_last_message.txt"
DIFF_FILE="$RUN_DIR/diff.patch"
STAT_FILE="$RUN_DIR/diff.stat"
NAMEONLY_FILE="$RUN_DIR/changed_files.txt"
TEST_FILE="$RUN_DIR/pytest.txt"
BUNDLE_FILE="$RUN_DIR/review_bundle.md"
REVIEW_PROMPT_FILE="$RUN_DIR/chatgpt_review_prompt.md"
META_FILE="$RUN_DIR/run_meta.txt"

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

printf '%s\n' "$PROMPT_CONTENT" > "$CODEX_PROMPT_FILE"
generate_story_context "$STORY_ID" "$STORY_CONTEXT_FILE" "$CONTEXT_MODE"
CONTEXT_FILES_CSV="$(printf '%s,' "${GENERATED_CONTEXT_FILES[@]}")"
CONTEXT_FILES_CSV="${CONTEXT_FILES_CSV%,}"
setup_isolated_worktree

info "Zumbot Codex pipeline starting"
info "Repo root: $ROOT_DIR"
info "Branch: $BRANCH_NAME"
info "HEAD: $CURRENT_HEAD"
info "Story id: $STORY_ID"
info "Prompt file: $PROMPT_FILE"
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
  "${cmd[@]}" < "$PROMPT_FILE" > "$LOG_FILE" 2>&1
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

CODEX_EXIT="$(run_codex)"

info "Collecting git artifacts"
git diff --stat "$REVIEW_DIFF_RANGE" > "$STAT_FILE" || true
git diff "$REVIEW_DIFF_RANGE" > "$DIFF_FILE" || true
git diff --name-only "$REVIEW_DIFF_RANGE" > "$NAMEONLY_FILE" || true

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
- run_timestamp_utc: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
- run_dir: $RUN_DIR
- context_mode: $CONTEXT_MODE
- isolated_run: yes
- isolated_worktree_dir: $WORKTREE_DIR
- isolated_worktree_head: $WORKTREE_HEAD
- isolated_worktree_cleanup: exit_trap
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
$REVIEW_DIFF_RANGE

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
  warn "Codex finished with non-zero exit code: $CODEX_EXIT"
fi

if [[ "$PYTEST_EXIT" != "0" && "$PYTEST_EXIT" != "SKIPPED" ]]; then
  warn "pytest finished with non-zero exit code: $PYTEST_EXIT"
fi
