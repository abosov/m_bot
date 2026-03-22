# File Scope — US-AUTO-41

## Files Allowed To Change
- `automation/bundle_packs/US-AUTO-41.bundle.md`
- `automation/bundles/active/US-AUTO-41/00_story.md`
- `automation/bundles/active/US-AUTO-41/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-41/02_file_scope.md`
- `automation/bundles/active/US-AUTO-41/03_master_prompt.md`
- `automation/bundles/active/US-AUTO-41/04_review_checklist.md`
- `automation/bundles/active/US-AUTO-41/05_followups.md`
- `automation/bundles/active/US-AUTO-41/06_manual_actions.md`
- `automation/scripts/commit_story_artifacts.sh`
- `automation/scripts/run_story.sh`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `tests/test_run_story.py`
- `tests/test_story_bundle_scripts.py`

## Files Not Allowed To Change
- rollback lifecycle implementation introduced by US-AUTO-38, except where strictly necessary for compatibility within `automation/scripts/run_story.sh`
- bundle generation semantics outside the US-AUTO-41 bundle artifacts listed above
- unrelated workflow scripts
- application code outside automation/docs/tests scope
- any tests other than:
  - `tests/test_run_story.py`
  - `tests/test_story_bundle_scripts.py`

## Implementation Notes
The new handoff script must allowlist only these artifact paths for `<STORY_ID>`:
- `automation/bundle_packs/<STORY_ID>.bundle.md`
- `automation/bundles/active/<STORY_ID>/**`

For this story, the bundle artifacts themselves are also part of the allowed changed-file scope because they are versioned and committed as part of the story branch before execution.

`run_story.sh` must remain strict and must not auto-commit. It may only improve targeted preflight messaging for dirty story artifacts.

## Test Notes
Cover at minimum:
- artifact-only commit succeeds
- unrelated changes cause failure
- nothing-to-commit causes failure
- `run_story.sh` blocks on dirty story artifacts and prints remediation

