# File Scope — US-AUTO-44

## Files Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/bundle_packs/US-AUTO-44.bundle.md`
- `automation/bundles/active/US-AUTO-44/00_story.md`
- `automation/bundles/active/US-AUTO-44/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-44/02_file_scope.md`
- `automation/bundles/active/US-AUTO-44/03_master_prompt.md`
- `automation/bundles/active/US-AUTO-44/04_review_checklist.md`
- `automation/bundles/active/US-AUTO-44/05_followups.md`
- `automation/bundles/active/US-AUTO-44/06_manual_actions.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `tests/test_run_story.py`

## Files Not Allowed To Change
- `automation/scripts/commit_story_artifacts.sh`
- `automation/run_codex_task.sh`
- review/classification/gate scripts
- rollback lifecycle logic
- unrelated workflow scripts
- application runtime code outside automation workflow docs/tests

## Rationale
This story is about explicit preflight classification and operator messaging in `run_story.sh`, not about changing artifact commit ownership or execution behavior. `commit_story_artifacts.sh` is already the explicit commit handoff boundary and must remain unchanged unless a later story explicitly targets it.

Because scope validation compares the full branch diff against `origin/main`, the canonical story bundle artifacts for US-AUTO-44 and the narrow run-story test file must be explicitly allowlisted for this story.

## Expected Test Surface
Use `tests/test_run_story.py` for narrowly scoped regression coverage around:
- clean tree passes preflight
- requested-story artifact dirtiness prints handoff message
- unrelated dirtiness prints cleanup/remediation message

## Path Rules
- No new broad utility modules.
- No cross-cutting refactor.
- Keep edits local to the workflow contract.