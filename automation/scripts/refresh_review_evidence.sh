#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${AUTOMATION_ROOT_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
RUNS_ROOT="${AUTOMATION_RUNS_ROOT:-$ROOT_DIR/automation/runs}"
EPHEMERAL_LEDGER_PATH="automation/story_change_ledger.jsonl"
EPHEMERAL_LEDGER_EXCLUDE_PATHSPEC=":(exclude)$EPHEMERAL_LEDGER_PATH"
REFRESH_MODE="no_codex_review_evidence_refresh"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

usage() {
  cat >&2 <<'EOF'
Usage:
  automation/scripts/refresh_review_evidence.sh STORY_ID
EOF
  exit 1
}

validate_story_id() {
  local story_id="$1"
  [[ "$story_id" =~ ^US-[A-Z0-9]+(-[A-Z0-9]+)*$ ]] || \
    fail "invalid STORY_ID '$story_id' (expected format like US-AUTO-60)"
}

working_tree_dirty() {
  local status_output
  status_output="$(git -C "$ROOT_DIR" status --porcelain --untracked-files=normal -- . "$EPHEMERAL_LEDGER_EXCLUDE_PATHSPEC" 2>/dev/null || true)"
  [[ -n "$status_output" ]]
}

resolve_review_base_ref() {
  if ! git -C "$ROOT_DIR" remote get-url origin >/dev/null 2>&1; then
    fail "origin remote is required to refresh review evidence"
  fi

  if ! git -C "$ROOT_DIR" fetch --quiet origin main; then
    fail "failed to fetch origin main before refreshing review evidence"
  fi

  if ! git -C "$ROOT_DIR" rev-parse --verify --quiet "origin/main^{commit}" >/dev/null 2>&1; then
    fail "origin/main is required to refresh review evidence"
  fi

  printf 'origin/main\n'
}

[[ $# -eq 1 ]] || usage

STORY_ID="$1"
validate_story_id "$STORY_ID"

git -C "$ROOT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1 || fail "not a git repository: $ROOT_DIR"

CURRENT_BRANCH="$(git -C "$ROOT_DIR" rev-parse --abbrev-ref HEAD)"
[[ "$CURRENT_BRANCH" != "main" ]] || fail "refresh is forbidden on main branch"

if working_tree_dirty; then
  fail "working tree is dirty; commit or discard changes before refresh"
fi

BUNDLE_DIR="$ROOT_DIR/automation/bundles/active/$STORY_ID"
[[ -d "$BUNDLE_DIR" ]] || fail "active story bundle not found: $BUNDLE_DIR"
[[ -f "$BUNDLE_DIR/02_file_scope.md" ]] || fail "story scope file not found: $BUNDLE_DIR/02_file_scope.md"

CURRENT_HEAD="$(git -C "$ROOT_DIR" rev-parse --verify HEAD)"
REVIEW_BASE_REF="$(resolve_review_base_ref)"
MERGE_BASE="$(git -C "$ROOT_DIR" merge-base "$REVIEW_BASE_REF" HEAD 2>/dev/null || true)"
[[ -n "$MERGE_BASE" ]] || MERGE_BASE="$REVIEW_BASE_REF"

RUN_ID="$(date -u +"%Y-%m-%d_%H-%M-%S")_refresh"
RUN_DIR="$RUNS_ROOT/$STORY_ID/$RUN_ID"
mkdir -p "$RUN_DIR"

git -C "$ROOT_DIR" diff --name-only "$MERGE_BASE" -- . "$EPHEMERAL_LEDGER_EXCLUDE_PATHSPEC" | LC_ALL=C sort -u > "$RUN_DIR/changed_files.txt"
git -C "$ROOT_DIR" diff "$MERGE_BASE" -- . "$EPHEMERAL_LEDGER_EXCLUDE_PATHSPEC" > "$RUN_DIR/diff.patch"

if [[ -s "$RUN_DIR/changed_files.txt" ]]; then
  CHANGED_FILES_DETECTED="yes"
else
  CHANGED_FILES_DETECTED="no"
fi

cat > "$RUN_DIR/review_bundle.md" <<EOF
# Review Bundle

- story_id: $STORY_ID
- refresh_mode: $REFRESH_MODE
- source_of_truth_head: $CURRENT_HEAD
- review_base_ref: $REVIEW_BASE_REF
- merge_base: $MERGE_BASE
EOF

cat > "$RUN_DIR/chatgpt_review_prompt.md" <<EOF
Review this Zumbot Codex change.

Context:
- Story ID: $STORY_ID
- Refresh mode: $REFRESH_MODE
- Reviewed HEAD: $CURRENT_HEAD
- Branch: $CURRENT_BRANCH
- Review diff source: $REVIEW_BASE_REF...HEAD
- Review artifact base: $MERGE_BASE
- Codex implementation rerun: not invoked

This is a no-Codex review-evidence refresh run. The implementation was already committed, and this prompt must review the committed diff represented by the artifacts below.

Pinned run directory:
$RUN_DIR

Use ONLY these artifact paths:
- $RUN_DIR/review_bundle.md
- $RUN_DIR/changed_files.txt
- $RUN_DIR/diff.patch
- $RUN_DIR/pytest.txt
- $RUN_DIR/refresh_review_evidence.json
- $RUN_DIR/manifest.md

Do not use automation/output unless it points to this exact pinned run.
If automation/output contains another story, branch, or stale review bundle, ignore it as unrelated evidence.

Review requirements:
1. architecture fit
2. scope creep
3. safety issues
4. hallucination or automation-risk issues
5. missing tests
6. missing docs
7. branch/workflow compliance
8. refresh-mode evidence fidelity

For refresh-mode evidence fidelity, verify:
- refresh_review_evidence.json exists and matches the story ID;
- refresh mode is $REFRESH_MODE;
- codex_invoked is false;
- reviewed HEAD matches the current committed implementation;
- diff.patch and changed_files.txt represent the $REVIEW_BASE_REF...HEAD review surface;
- the refresh path does not hide stale evidence or bypass review/classify/gate safety.

Return a structured review with exactly these top-level headings:
# AI Review
# AI Review Result
EOF

if [[ -z "${AUTOMATION_REFRESH_PYTEST_CMD:-}" ]]; then
  fail "AUTOMATION_REFRESH_PYTEST_CMD is required for refresh pytest evidence; provide a story-scoped pytest command"
fi

REFRESH_PYTEST_CMD="$AUTOMATION_REFRESH_PYTEST_CMD"
set +e
bash -lc "$REFRESH_PYTEST_CMD" > "$RUN_DIR/pytest.txt" 2>&1
PYTEST_EXIT_CODE=$?
set -e

if [[ "$PYTEST_EXIT_CODE" -ne 0 ]]; then
  fail "refresh pytest command failed with exit code $PYTEST_EXIT_CODE; see $RUN_DIR/pytest.txt"
fi

cat > "$RUN_DIR/manifest.md" <<EOF
# Review Evidence Refresh Manifest

- story_id: $STORY_ID
- branch: $CURRENT_BRANCH
- starting_head: $CURRENT_HEAD
- isolated_worktree_head: $CURRENT_HEAD
- review_base_ref: $REVIEW_BASE_REF
- review_artifact_base: $MERGE_BASE
- materialization_status: not_needed
- pytest_exit_code: $PYTEST_EXIT_CODE
- changed_files_detected: $CHANGED_FILES_DETECTED
- refresh_mode: $REFRESH_MODE
- codex_invoked: false

## Artifacts
- manifest.md
- changed_files.txt
- diff.patch
- review_bundle.md
- chatgpt_review_prompt.md
- pytest.txt
- refresh_review_evidence.json
EOF

python3 - "$RUN_DIR/refresh_review_evidence.json" "$STORY_ID" "$CURRENT_HEAD" "$CURRENT_BRANCH" "$REVIEW_BASE_REF" "$MERGE_BASE" "$REFRESH_MODE" "$RUN_DIR" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

output = Path(sys.argv[1])
story_id = sys.argv[2]
current_head = sys.argv[3]
current_branch = sys.argv[4]
base_ref = sys.argv[5]
merge_base = sys.argv[6]
refresh_mode = sys.argv[7]
run_dir = Path(sys.argv[8])

payload = {
    "story_id": story_id,
    "current_head": current_head,
    "current_branch": current_branch,
    "base_ref": base_ref,
    "merge_base": merge_base,
    "refresh_mode": refresh_mode,
    "codex_invoked": False,
    "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
      "evidence_paths": {
          "run_dir": str(run_dir),
          "manifest": str(run_dir / "manifest.md"),
          "changed_files": str(run_dir / "changed_files.txt"),
          "diff_patch": str(run_dir / "diff.patch"),
          "review_bundle": str(run_dir / "review_bundle.md"),
          "chatgpt_review_prompt": str(run_dir / "chatgpt_review_prompt.md"),
          "pytest": str(run_dir / "pytest.txt"),
          "refresh_review_evidence": str(run_dir / "refresh_review_evidence.json"),
      },
}

output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

cat > "$RUN_DIR/run_meta.txt" <<EOF
story_id=$STORY_ID
branch=$CURRENT_BRANCH
head=$CURRENT_HEAD
review_base_ref=$REVIEW_BASE_REF
review_diff_range=$MERGE_BASE...$CURRENT_HEAD
run_dir=$RUN_DIR
run_id=$RUN_ID
status=success
refresh_mode=$REFRESH_MODE
codex_invoked=false
timestamp_utc=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
EOF

printf 'Refresh evidence written: %s\n' "$RUN_DIR"
printf 'Analyze next: AUTOMATION_RUN_DIR=%q automation/scripts/analyze_story_run.sh %q\n' "$RUN_DIR" "$STORY_ID"
