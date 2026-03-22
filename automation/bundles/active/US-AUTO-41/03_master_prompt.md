# Master Prompt — US-AUTO-41

## Role
You are a senior workflow engineer, shell-script implementer, test author, and technical writer working inside the Zumbot US-AUTO automation contract.

## Goal
Implement **US-AUTO-41 — Story artifacts commit handoff before run** as a narrow workflow-contract story. Add a canonical explicit commit handoff step between materialization and execution without weakening the clean-tree boundary.

## Source of Truth
- `automation/scripts/new_story_bundle.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/run_story.sh`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Files Allowed To Change
- `automation/scripts/commit_story_artifacts.sh`
- `automation/scripts/run_story.sh`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- only the minimum test files required for this story

## Files Not Allowed To Change
- unrelated workflow scripts
- application runtime code unrelated to story execution workflow
- rollback contract logic except where explicitly necessary for compatibility

## Requirements
1. Add `automation/scripts/commit_story_artifacts.sh <STORY_ID>`.
2. The script must only stage and commit:
   - `automation/bundle_packs/<STORY_ID>.bundle.md`
   - `automation/bundles/active/<STORY_ID>/**`
3. The script must fail on unrelated dirty paths anywhere else in the repo.
4. The script must fail when no eligible changes exist.
5. The script must use a deterministic commit message.
6. `run_story.sh` must block on dirty story artifacts and print a deterministic remediation hint.
7. Update docs and registry.
8. Add or update tests.

## Constraints
- do not weaken clean-tree enforcement
- do not implement implicit auto-commit inside `run_story.sh`
- do not opportunistically refactor unrelated code
- use allowlist path matching, not broad exclusions

## Output
Deliver:
- implementation of the new handoff script
- minimal update to `run_story.sh`
- tests
- doc updates
- epic registry update

Before finishing:
- run relevant tests
- verify docs match behavior
- confirm no unrelated files changed

