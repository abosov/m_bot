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
- `automation/scripts/run_story.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/finalize_story.sh`
- `automation/scripts/story_change_ledger.sh`
- `automation/story_change_ledger.jsonl`
- `tests/test_story_change_ledger.py`
- `tests/test_review_gate_story_run.py`
- `tests/test_finalize_story_script.py`
- `automation/run_codex_task.sh`

## Files Not Allowed To Change
- `backend/**`
- `frontend/**`
- `database/**`
- `migrations/**`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `tests/test_story_bundle_scripts.py`
- broad review-gate or merge-contract redesign unrelated to recording existing lifecycle outcomes
- any story files outside `US-AUTO-23` except the shared docs and registry listed above

## Scope Notes
Allowed change pattern:
- add one append-only story ledger artifact
- add one small ledger helper
- append lifecycle entries at start, review outcome, and finalize outcome checkpoints
- add focused tests for the changed lifecycle scripts and ledger helper
- update docs/checklist/registry to describe the ledger as evidence-only

Disallowed change pattern:
- introducing stop/continue policy
- adding loop scoring or heuristics
- redesigning stage/resume logic
- adding operator dashboards or summaries
- broad cleanup or unrelated refactors in automation scripts

If implementation requires a wider surface than the exact files above, stop and capture a follow-up instead of widening the story.