# US-AUTO-23 PROMPT 1

## Role
You are the System Architect + Data Architect + Developer + QA + Security Reviewer for Zumbot.

## Goal
Implement only the durable story ledger primitive for `US-AUTO-23`:
- add one repository-visible append-only ledger artifact
- add one small append helper
- record lifecycle events at minimal stable checkpoints for story start, review outcome, and finalize outcome
- add focused tests
- update docs/checklist/registry accordingly

## Source of Truth
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `automation/bundles/active/US-AUTO-23/00_story.md`
- `automation/bundles/active/US-AUTO-23/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-23/02_file_scope.md`

## Required First Response
Before editing anything:
1. restate the one-sentence intent in your own words
2. confirm that this story is evidence-only and does not implement enforcement
3. name the minimal lifecycle checkpoints you intend to touch

## Constraints
- Keep the implementation as small and deterministic as possible.
- Prefer a compact normalized entry shape.
- Accept missing optional metadata gracefully.
- Keep event vocabulary intentionally narrow.
- Favor fewer touched files and fewer lifecycle call sites.
- Do not modify bundle tooling tests or general bundle validation tests for this story.

## Files Allowed To Change
See `automation/bundles/active/US-AUTO-23/02_file_scope.md`.

## Files Not Allowed To Change
See `automation/bundles/active/US-AUTO-23/02_file_scope.md`.

## Hard Stops
If implementation would require any of the following, do not implement it in this story; document it as a follow-up instead:
- using the ledger to decide whether a story may run
- retry or rerun counters with blocking semantics
- loop-risk scoring or heuristics
- pipeline zone caps
- escalation policy
- merge recommendation redesign
- operator dashboarding or UX expansion
- changes outside allowed files
- changes to `tests/test_story_bundle_scripts.py`

## Output
Return:
1. changed files summary
2. implementation rationale
3. exact lifecycle integration points used
4. tests run and results
5. risks or follow-ups discovered but not implemented
6. final diff summary