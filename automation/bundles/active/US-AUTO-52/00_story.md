# US-AUTO-52 — Strict manual-finish continuation contract

## Story ID and Title
US-AUTO-52 — Strict manual-finish continuation contract

## Objective
Narrow the manual-finish continuation rule so that continuation is allowed only for the exact committed manual-finish case that completes a previously blocked non-converging rerun, and rejected for any broader ancestor-based or descendant-based scenario.

## Scope
This story is limited to the continuation predicate and its direct regression coverage for the analyze/review continuation boundary. The implementation must preserve the existing fail-closed review pipeline and must not broaden scope into unrelated review UX, rerun orchestration, or registry automation.

## Non-goals
- Do not redesign the overall manual-finish workflow.
- Do not change `run_story.sh` rerun behavior.
- Do not alter unrelated review gate classification semantics.
- Do not modify story bundle validator contracts.
- Do not change tests to weaken existing external behavior contracts.

## Dependencies
- Implemented/manual evidence from US-AUTO-47 rerun convergence boundary.
- Implemented/manual evidence from US-AUTO-50 AI review artifact contract stabilization.
- Rejected follow-up evidence from US-AUTO-51 showing the continuation path works but is too broad.
- Existing pipeline invariant: review-stage commands must operate on committed HEAD and fail closed on stale or divergent evidence.

## Source of Truth
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `tests/test_analyze_story_run.py`
- `tests/test_classify_review_story_run.py`
- `tests/test_review_gate_story_run.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Current Code Reality
US-AUTO-51 proved that the manual-finish continuation path can move a blocked non-converging rerun into a continuation-ready state and allow pinned `analyze`, `ai_review`, `classify`, and `gate` to proceed. However, review evidence also showed that the continuation predicate is broader than intended: it allows continuation based on ancestor-of-HEAD logic instead of requiring the exact committed manual-finish case. Current regression coverage also reinforces that broadened interpretation, creating a merge blocker because the contract is no longer strict and fail-closed for stale-run scenarios.

## Target Outcome
The continuation predicate must allow exactly one narrow case:
1. a previously blocked run recorded a non-converging rerun/manual-finish-required state for a specific committed reviewed head, and
2. the current checkout HEAD is the exact committed manual-finish continuation case associated with that blocked run.

All other stale-run scenarios must remain rejected, including:
- descendant commits after the manual-finish commit,
- ancestor-based generalization,
- unrelated HEAD advancement,
- workspace-only divergence,
- missing or inconsistent run evidence.

## Atomic Task Isolation Contract
This story may only tighten the continuation predicate and update the minimal supporting regression tests and documentation that directly describe that predicate. No other behavior changes are allowed. If implementation pressure suggests touching additional scripts, pipeline stages, or contracts outside this boundary, stop and record that as a follow-up instead of widening the story.

## Risks
- Medium risk of accidental contract drift if the predicate is implemented in multiple places inconsistently.
- Medium risk of regression if tests are updated to match implementation rather than enforcing the exact-case contract.
- Low-to-medium risk of hidden coupling with gate/classification messaging if stale-evidence reasoning is reused across scripts.

## Manual Actions
- Update the registry so US-AUTO-51 remains a rejected/blocked follow-up source rather than being marked implemented.
- Add US-AUTO-52 as the next recommended P1 corrective story.
- After implementation commit, rerun the story from a fresh feature-branch HEAD and do not reuse an old `AUTOMATION_RUN_DIR`.
- Review pinned artifacts only after the rerun generated from the current commit.

## Acceptance Notes
- Exact committed manual-finish continuation case passes.
- Descendant commit after manual finish rejects.
- Ancestor-based continuation rejects.
- Existing stale-run fail-closed protections remain intact.
- Materialized bundle validates cleanly.
- Review outcome is deterministic for the exact-case contract and fail-closed otherwise.

