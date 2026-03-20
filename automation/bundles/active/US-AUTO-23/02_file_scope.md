# US-AUTO-23: File Scope

## Files Allowed To Change
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `automation/bundle_packs/US-AUTO-23.bundle.md`
- `automation/bundles/active/US-AUTO-23/00_story.md`
- `automation/bundles/active/US-AUTO-23/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-23/02_file_scope.md`
- `automation/bundles/active/US-AUTO-23/03_master_prompt.md`
- `automation/bundles/active/US-AUTO-23/04_review_checklist.md`
- `automation/bundles/active/US-AUTO-23/05_followups.md`
- `automation/bundles/active/US-AUTO-23/06_manual_actions.md`
- one new ledger artifact path under `automation/`
- one new ledger writer helper under `automation/scripts/` or a nearby automation utility path
- only the minimal existing lifecycle scripts needed to append entries at canonical checkpoints
- focused tests for the changed automation logic

## Files Not Allowed To Change
- `backend/**`
- `frontend/**`
- `database/**`
- `migrations/**`
- `automation/scripts/run_codex_task.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- broad review-gate or merge-contract redesign unrelated to recording existing lifecycle outcomes
- any story files outside `US-AUTO-23` except the shared docs and registry listed above

## Scope Notes
Allowed change pattern:
- add ledger artifact
- add ledger append helper
- inject append calls into minimal lifecycle checkpoints
- add focused tests
- update docs to explain the ledger as evidence-only

Disallowed change pattern:
- introducing stop/continue policy
- adding loop scoring or heuristics
- redesigning stage/resume logic
- adding operator dashboards or summaries
- broad cleanup or unrelated refactors in automation scripts

If implementation requires a materially wider surface than the items above, stop and capture a follow-up instead of widening the story.