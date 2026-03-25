# File Scope — US-AUTO-44

## Files Allowed To Change
- `automation/scripts/run_story.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- only the minimum test files required for this story

## Files Not Allowed To Change
- `automation/scripts/commit_story_artifacts.sh`
- `automation/run_codex_task.sh`
- review/classification/gate scripts
- rollback lifecycle logic
- unrelated workflow scripts
- application runtime code outside automation workflow docs/tests

## Rationale
This story is about explicit preflight classification and operator messaging in `run_story.sh`, not about changing artifact commit ownership or execution behavior. `commit_story_artifacts.sh` is already the explicit commit handoff boundary and must remain unchanged unless later story explicitly targets it.

## Expected Test Surface
Use the minimum existing test modules that already cover `run_story.sh` behavior. Add narrowly scoped tests for:
- clean tree passes preflight
- requested-story artifact dirtiness prints handoff message
- unrelated dirtiness prints cleanup/remediation message

## Path Rules
- No new broad utility modules.
- No cross-cutting refactor.
- Keep edits local to the workflow contract.

