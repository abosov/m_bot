# Story Bundle Pack
Story-ID: US-AUTO-52
Version: 1

=== FILE: 00_story.md ===
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

=== FILE: 01_context_bundle.md ===
# Context Bundle — US-AUTO-52

## Source of Truth
Primary implementation and verification files for this story are:
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `tests/test_analyze_story_run.py`
- `tests/test_classify_review_story_run.py`
- `tests/test_review_gate_story_run.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Current Code Reality
The current pipeline already demonstrates the important architectural fact: manual finish can produce a continuation-ready path for a previously blocked non-converging rerun. That removes the older “impossible to continue review after manual finish” blocker in principle. The remaining defect is narrower and contractual: the continuation predicate accepts a broader ancestry relationship than intended. Review evidence also shows stale verification artifacts relative to the latest HEAD, which is expected once a manual-finish commit advances the branch after the reviewed run. The corrective story must not re-open the solved part of the problem; it must only tighten the acceptance boundary for continuation.

## Architectural Intent
The pipeline must remain deterministic, committed-HEAD-based, and fail-closed. Manual finish is not a generic stale-run escape hatch. It is a tightly scoped recovery path for one specific committed case: the exact manual-finish commit that completes the previously blocked run. The architecture should preserve these invariants:
- review stages never silently reinterpret stale evidence,
- continuation does not follow general ancestry,
- exact-case recovery is allowed only when run evidence explicitly supports it,
- all other cases reject with deterministic stale-run behavior.

## Risks
- Over-correcting could disable the valid exact-case continuation path that US-AUTO-51 proved.
- Under-correcting could leave ancestor-based continuation in place and keep the contract too permissive.
- Partial fixes in only one script could create inconsistent analyze/classify/gate outcomes.
- Broad documentation edits could drift from the narrow implementation intent.

## Acceptance Notes
A valid implementation for this story should show:
- exact-case continuation allowed,
- descendant-of-manual-finish continuation blocked,
- ancestor-based continuation blocked,
- no broadening of scope into unrelated review or rerun flow,
- deterministic pinned-run review behavior preserved.

=== FILE: 02_file_scope.md ===
# File Scope — US-AUTO-52

## Files Allowed To Change
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `tests/test_analyze_story_run.py`
- `tests/test_classify_review_story_run.py`
- `tests/test_review_gate_story_run.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Files Not Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/run_codex_task.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/story_change_ledger.jsonl`
- any files under `automation/bundle_packs/` other than the materialized US-AUTO-52 artifacts created by workflow
- any files under `automation/bundles/active/` other than the materialized US-AUTO-52 artifacts created by workflow
- any unrelated tests or docs outside the files explicitly allowed above

## Scope Notes
- Allowed change types are limited to: tightening the manual-finish continuation predicate, aligning cross-script reasoning for the same predicate, adding exact regression tests for strict acceptance/rejection cases, and updating checklist/registry text to reflect the new corrective story.
- Do not widen scope into retry strategy, manual-finish UX, new operator prompts, or generalized stale-evidence recovery.
- Do not weaken tests to make the implementation pass; tests must enforce the strict external contract.
- `docs/90_codex/epics/US-AUTO_REGISTRY.md` changes must only reflect status/priority/next-story logic for US-AUTO-51, US-AUTO-52, and the dependency note for US-AUTO-28-F1.

=== FILE: 03_master_prompt.md ===
# Master Prompt — US-AUTO-52

## Role
You are the implementation engineer for the US-AUTO pipeline, working under strict fail-closed governance and atomic task isolation.

## Goal
Implement a strict manual-finish continuation contract so that continuation is allowed only for the exact committed manual-finish case tied to a previously blocked non-converging rerun, and rejected for broader ancestor-based or descendant-based cases.

## Source of Truth
Use only these files as the source of truth for this story:
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `tests/test_analyze_story_run.py`
- `tests/test_classify_review_story_run.py`
- `tests/test_review_gate_story_run.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Files Allowed To Change
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `tests/test_analyze_story_run.py`
- `tests/test_classify_review_story_run.py`
- `tests/test_review_gate_story_run.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Files Not Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/run_codex_task.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/story_change_ledger.jsonl`
- any unrelated tests, scripts, docs, or workflow helpers outside the allowed list

## Atomic Task Isolation Contract
This is a narrow corrective follow-up. You may not redesign pipeline flow, create new recovery modes, or touch unrelated review stages. The only permitted functional change is tightening the continuation predicate and aligning direct regression coverage/documentation for that exact contract. If a desired fix requires broadening scope, stop and record a follow-up instead of implementing it.

## Execution Gate
Before making changes, verify that the intended edits remain within the allowed files and directly support the strict exact-case continuation contract. If you find yourself needing to:
- alter run orchestration,
- change AI review generation,
- modify bundle validator behavior,
- adjust unrelated stale-head policies,
then stop because the story boundary would be violated.

## Implementation Requirements
1. Preserve the proven capability that a valid manual-finish continuation path can proceed.
2. Remove any ancestor-based continuation logic that permits broader-than-intended acceptance.
3. Require the exact committed manual-finish case associated with the blocked run evidence.
4. Ensure analyze/classify/gate interpret that exact-case rule consistently.
5. Keep the implementation fail-closed when evidence is missing, stale, inconsistent, or refers to a different HEAD relationship.
6. Do not add fallback heuristics or best-effort continuation behavior.
7. Update documentation only as needed to describe the strict contract and the corrective story sequencing in the registry.

## Verification Requirements
You must verify, at minimum:
- exact allowed case passes,
- descendant commit after manual finish rejects,
- ancestor-based continuation rejects,
- existing committed-HEAD and stale-run protections still pass,
- no unrelated tests or files were changed.

Use targeted pytest coverage for the touched scripts. The implementation is not complete until regression tests explicitly prove the narrow exact-case behavior.

## Output
Produce only the implementation required for this story. Keep changes minimal and deterministic. Do not include speculative follow-ups in code. If additional defects are discovered, record them in documentation or follow-up notes without widening the implementation.

=== FILE: 04_review_checklist.md ===
# Review Checklist — US-AUTO-52

## Scope Validation
- APPROVE only if changed files are limited to the allowed scope.
- REJECT if any file outside the allowed list changed.
- REJECT if the story mixes continuation contract tightening with unrelated UX, orchestration, retry, or validator changes.
- REJECT if the registry update claims implementation/closure for US-AUTO-51 instead of recording it as a rejected corrective predecessor.

## Functional Validation
- APPROVE only if the implementation allows continuation for the exact committed manual-finish case tied to the blocked run evidence.
- REJECT if continuation is still allowed for any ancestor-of-HEAD generalization.
- REJECT if continuation is allowed for descendant commits after the manual-finish commit.
- REJECT if the valid exact-case continuation path is accidentally disabled.
- REJECT if analyze/classify/gate disagree about the same continuation boundary.

## Verification
- APPROVE only if targeted regression tests prove:
  - exact allowed case passes,
  - descendant case rejects,
  - ancestor-based case rejects.
- REJECT if tests were weakened instead of enforcing the contract.
- REJECT if verification artifacts are stale relative to the commit under review.
- REJECT if review outcome depends on workspace-only changes or non-committed state.

=== FILE: 05_followups.md ===
# Follow-Ups — US-AUTO-52

## Follow-Up Prompt Queue
- If additional operator guidance is needed after this fix, create a separate story for manual-finish review UX; do not extend US-AUTO-52.
- If registry/status automation becomes noisy, create a separate registry-maintenance story; do not expand this fix.
- If other stale-evidence branches need tightening beyond the exact manual-finish case, create separate atomic follow-ups per branch of behavior.

## Iteration Notes
- US-AUTO-51 remains valuable because it proved the continuation path is viable in principle.
- US-AUTO-52 exists only to tighten the acceptance contract to exact-case semantics.
- US-AUTO-28-F1 should remain blocked pending this stricter corrective story, not pending further silent edits to US-AUTO-51.
- After this story, any remaining issues should be framed as new narrow follow-ups rather than retroactively widening the current scope.

=== FILE: 06_manual_actions.md ===
# Manual Actions — US-AUTO-52

## Required Human Actions
1. Save this bundle pack to `automation/bundle_packs/US-AUTO-52.bundle.md`.
2. Run `automation/scripts/materialize_story_bundle.sh US-AUTO-52`.
3. Run `automation/scripts/validate_story_bundle.sh US-AUTO-52`.
4. Update `docs/90_codex/epics/US-AUTO_REGISTRY.md` consistently with this bundle:
   - mark US-AUTO-51 as blocked/rejected follow-up required,
   - add US-AUTO-52 as the current P1 next recommended corrective story,
   - keep US-AUTO-28-F1 blocked pending US-AUTO-52.
5. Create a new feature branch for US-AUTO-52. Do not run automation on `main`.
6. Commit the story artifacts for US-AUTO-52 before implementation work.
7. Implement the strict continuation fix only within the allowed files.
8. Run targeted pytest coverage for the touched scripts.
9. Run `automation/scripts/run_story.sh US-AUTO-52` from the current feature-branch HEAD.
10. After any new commit, treat prior `AUTOMATION_RUN_DIR` values as invalid and rerun the story before review-stage commands.
11. Run `automation/scripts/analyze_story_run.sh US-AUTO-52` on the fresh run.
12. Proceed with pinned review-stage commands only for the rerun produced from the current committed HEAD.

## Completion Status
- Bundle drafted for US-AUTO-52.
- Registry logic intended: US-AUTO-52 becomes the active corrective P1 follow-up.
- Implementation, verification, rerun, and review are pending.