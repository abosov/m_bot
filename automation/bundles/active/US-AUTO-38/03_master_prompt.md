# US-AUTO-38 PROMPT 1 — Automatic rollback after failed automation run

## Role
You are the System Architect, Shell Workflow Engineer, Test Engineer, and Tech Writer for Zumbot.

## Story
US-AUTO-38 — Automatic rollback after failed automation run.

## Goal
Implement a deterministic automatic rollback contract so failed or interrupted automation runs restore the exact clean pre-run repository state, while successful runs preserve intended changes and US-AUTO-37 behavior remains intact.

## Source of Truth
- `automation/scripts/run_story.sh`
- `automation/run_codex_task.sh`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- tests covering story execution behavior
- merged US-AUTO-37 behavior

## Files Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/run_codex_task.sh`
- `tests/test_run_story*.py`
- `tests/test_run_codex_task*.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`

## Files Not Allowed To Change
- `backend/**`
- `frontend/**`
- `database/**`
- `migrations/**`
- unrelated finalize redesign
- story registry redesign
- unrelated review gate policy
- unrelated deployment work

## Implementation Requirements
1. Rollback applies only when execution starts from a clean tree.
2. Top-level orchestration must own rollback lifecycle.
3. Rollback is armed after baseline capture and disarmed only at explicit success boundary.
4. Any failed run path must restore tracked changes and clean run-owned untracked artifacts.
5. Interrupted execution should be treated as failure where supported.
6. Rollback failure must surface loudly and must never masquerade as success.
7. US-AUTO-37 ephemeral path behavior must not regress.

## Guardrails
- Do not broaden cleanup beyond run-owned scope without clear justification.
- Do not add hidden auto-stash or auto-commit behavior unless explicitly justified and documented.
- Do not scatter rollback ownership across multiple unrelated scripts.
- If broader workflow redesign is required, stop and capture it as a follow-up.

## Output
Return:
1. changed files summary
2. design rationale
3. tests run
4. risks / follow-ups
5. final diff

