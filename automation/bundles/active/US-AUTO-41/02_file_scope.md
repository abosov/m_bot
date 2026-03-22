# File Scope — US-AUTO-41

## Files Allowed To Change
- `automation/scripts/commit_story_artifacts.sh`
- `automation/scripts/run_story.sh`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- test files needed to cover the new handoff script and updated run preflight behavior

## Files Not Allowed To Change
- rollback lifecycle implementation introduced by US-AUTO-38, except where strictly necessary for test compatibility
- bundle generation semantics outside documentation
- unrelated workflow scripts
- application code outside automation/docs/tests scope

## Implementation Notes
The new handoff script must allowlist only these artifact paths for `<STORY_ID>`:
- `automation/bundle_packs/<STORY_ID>.bundle.md`
- `automation/bundles/active/<STORY_ID>/**`

It must fail on unrelated tracked or untracked changes.

`run_story.sh` must remain strict and must not auto-commit. It may only improve targeted preflight messaging for dirty story artifacts.

## Test Notes
Cover at minimum:
- artifact-only commit succeeds
- unrelated changes cause failure
- nothing-to-commit causes failure
- `run_story.sh` blocks on dirty story artifacts and prints remediation

