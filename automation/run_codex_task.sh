#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)"
PROMPT_FILE="${1:-$ROOT_DIR/automation/prompts/current_task.md}"
OUTPUT_DIR="$ROOT_DIR/automation/output"

LOG_FILE="$OUTPUT_DIR/codex.log"
LAST_MESSAGE_FILE="$OUTPUT_DIR/codex_last_message.txt"
DIFF_FILE="$OUTPUT_DIR/diff.patch"
STAT_FILE="$OUTPUT_DIR/diff.stat"
NAMEONLY_FILE="$OUTPUT_DIR/changed_files.txt"
TEST_FILE="$OUTPUT_DIR/pytest.txt"
BUNDLE_FILE="$OUTPUT_DIR/review_bundle.md"
REVIEW_PROMPT_FILE="$OUTPUT_DIR/chatgpt_review_prompt.md"
META_FILE="$OUTPUT_DIR/run_meta.txt"

mkdir -p "$OUTPUT_DIR"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

info() {
  info() {
  echo "[INFO] $*" >&2
  }
}

warn() {
  echo "[WARN] $*"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "required command not found: $1"
}

require_cmd git
require_cmd bash
require_cmd codex
require_cmd pytest

[[ -f "$PROMPT_FILE" ]] || fail "prompt file not found: $PROMPT_FILE"

BRANCH_NAME="$(git rev-parse --abbrev-ref HEAD)"
CURRENT_HEAD="$(git rev-parse --short HEAD)"
GIT_STATUS="$(git status --porcelain)"

[[ "$BRANCH_NAME" != "main" ]] || fail "do not run automation on main; switch to a feature branch first"
[[ -z "$GIT_STATUS" ]] || fail "working tree is not clean; commit/stash changes first"

PROMPT_CONTENT="$(cat "$PROMPT_FILE")"
[[ -n "$PROMPT_CONTENT" ]] || fail "prompt file is empty: $PROMPT_FILE"

SKIP_PYTEST="${SKIP_PYTEST:-0}"
PYTEST_TARGET="${PYTEST_TARGET:-}"
CODEX_MODEL="${CODEX_MODEL:-}"
CODEX_EXTRA_ARGS="${CODEX_EXTRA_ARGS:-}"

rm -f \
  "$LOG_FILE" \
  "$LAST_MESSAGE_FILE" \
  "$DIFF_FILE" \
  "$STAT_FILE" \
  "$NAMEONLY_FILE" \
  "$TEST_FILE" \
  "$BUNDLE_FILE" \
  "$REVIEW_PROMPT_FILE" \
  "$META_FILE"

info "Zumbot Codex pipeline starting"
info "Repo root: $ROOT_DIR"
info "Branch: $BRANCH_NAME"
info "HEAD: $CURRENT_HEAD"
info "Prompt file: $PROMPT_FILE"
info "Output dir: $OUTPUT_DIR"

cat > "$META_FILE" <<META
branch=$BRANCH_NAME
head=$CURRENT_HEAD
prompt_file=$PROMPT_FILE
output_dir=$OUTPUT_DIR
timestamp_utc=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
META

run_codex() {
  local -a cmd
  cmd=(codex exec --full-auto -C "$ROOT_DIR" -o "$LAST_MESSAGE_FILE")

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
  printf '[INFO] Command:'
  printf ' %q' "${cmd[@]}"
  printf '\n'

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
git diff --stat > "$STAT_FILE" || true
git diff > "$DIFF_FILE" || true
git diff --name-only > "$NAMEONLY_FILE" || true

if [[ "$SKIP_PYTEST" == "1" ]]; then
  PYTEST_EXIT="SKIPPED"
  echo "pytest skipped by SKIP_PYTEST=1" > "$TEST_FILE"
else
  PYTEST_EXIT="$(run_pytest)"
fi

CHANGED_FILES="$(cat "$NAMEONLY_FILE" 2>/dev/null || true)"
DIFF_STAT_CONTENT="$(cat "$STAT_FILE" 2>/dev/null || true)"
PYTEST_OUTPUT_CONTENT="$(cat "$TEST_FILE" 2>/dev/null || true)"
DIFF_CONTENT="$(cat "$DIFF_FILE" 2>/dev/null || true)"
CODEX_LOG_CONTENT="$(cat "$LOG_FILE" 2>/dev/null || true)"
LAST_MESSAGE_CONTENT="$(cat "$LAST_MESSAGE_FILE" 2>/dev/null || true)"

cat > "$BUNDLE_FILE" <<BUNDLE
# Zumbot Codex Review Bundle

## Run metadata
- Branch: $BRANCH_NAME
- Base HEAD before run: $CURRENT_HEAD
- Prompt file: $PROMPT_FILE
- Codex exit code: $CODEX_EXIT
- Pytest exit code: $PYTEST_EXIT

## Changed files
\`\`\`
$CHANGED_FILES
\`\`\`

## Diff stat
\`\`\`
$DIFF_STAT_CONTENT
\`\`\`

## Codex last message
\`\`\`
$LAST_MESSAGE_CONTENT
\`\`\`

## Pytest output
\`\`\`
$PYTEST_OUTPUT_CONTENT
\`\`\`

## Codex log
\`\`\`
$CODEX_LOG_CONTENT
\`\`\`

## Unified diff
\`\`\`diff
$DIFF_CONTENT
\`\`\`
BUNDLE

cat > "$REVIEW_PROMPT_FILE" <<REVIEW
Проведи review изменений в проекте Zumbot.

Проверь строго по критериям:

1. Архитектура
- соблюдены ли layer boundaries
- изменение внесено в правильный слой
- нет ли лишних изменений вне scope задачи

2. Данные и БД
- нет ли duplicate source of truth
- если затронута схема БД: изменения должны идти через SQL migration
- ORM не должен добавлять server_default
- нет ли опасных расхождений между ORM и миграциями

3. API и backend
- зарегистрированы ли новые endpoints в router hierarchy
- нет ли сломанной связности между API / services / ORM
- не появился ли код вне задачи

4. UX/UI
- если изменение касается интерфейса: логичен ли UX, консистентны ли тексты и поведение

5. Документация
- обновлены ли нужные .md файлы
- достаточно ли синхронизирована документация с кодом

6. QA
- есть ли нужные тесты
- достаточны ли regression checks
- видно ли потенциально непротестированное поведение

7. Безопасность
- нет ли утечек чувствительных данных
- корректны ли auth / admin checks
- есть ли audit logging для destructive/admin operations

8. Deployment / ops risks
- есть ли риски для manual deploy
- нужны ли дополнительные smoke checks
- есть ли скрытые риски для VPS

Формат ответа:
- Что сделано хорошо
- Проблемы / риски
- Что обязательно исправить до merge
- Что можно улучшить позже

Ниже review bundle:

$(cat "$BUNDLE_FILE")
REVIEW

info "Artifacts generated:"
info "  $LOG_FILE"
info "  $LAST_MESSAGE_FILE"
info "  $STAT_FILE"
info "  $NAMEONLY_FILE"
info "  $DIFF_FILE"
info "  $TEST_FILE"
info "  $BUNDLE_FILE"
info "  $REVIEW_PROMPT_FILE"
info "  $META_FILE"

if [[ "$CODEX_EXIT" != "0" ]]; then
  warn "Codex finished with non-zero exit code: $CODEX_EXIT"
fi

if [[ "$PYTEST_EXIT" != "0" && "$PYTEST_EXIT" != "SKIPPED" ]]; then
  warn "pytest finished with non-zero exit code: $PYTEST_EXIT"
fi

info "Done"
