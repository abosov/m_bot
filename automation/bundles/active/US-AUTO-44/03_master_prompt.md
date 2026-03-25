# Master Prompt — US-AUTO-44

## Role
You are a senior workflow engineer, shell-script implementer, test author, and technical writer working inside the Zumbot US-AUTO automation contract.

## Goal
Implement **US-AUTO-44 — materialization preflight & operator handoff** as a narrow workflow-contract story. Make preflight in `run_story.sh` explicit, deterministic, and operator-readable without weakening existing clean-tree enforcement.

## Source of Truth
- `automation/scripts/run_story.sh`
- `automation/scripts/commit_story_artifacts.sh`
- `automation/run_codex_task.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

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

## Requirements
1. Add an explicit preflight stage to `automation/scripts/run_story.sh`.
2. Preflight must classify dirty paths for the requested story using narrow allowlist logic.
3. If only requested-story artifact paths are dirty, print a deterministic operator handoff message that instructs the operator to:
   - review changes
   - run `automation/scripts/commit_story_artifacts.sh <STORY_ID>`
   - rerun `automation/scripts/run_story.sh <STORY_ID>`
4. If unrelated dirty paths exist, print a deterministic blocked message instructing the operator to resolve those changes outside the story-artifact handoff flow.
5. Keep clean-tree enforcement fail-closed.
6. Do not introduce auto-commit, auto-stash, or auto-cleanup behavior.
7. Update documentation and epic registry to describe preflight as a first-class workflow stage.
8. Add or update tests for clean, story-artifact-dirty, and unrelated-dirty scenarios.

## Constraints
- do not weaken clean-tree enforcement
- do not modify `commit_story_artifacts.sh`
- do not move commit ownership into `run_story.sh`
- do not broaden scope into materialization redesign
- use deterministic, testable messages
- keep the patch minimal and local

## Output
Deliver:
- minimal `run_story.sh` preflight implementation
- narrow tests
- doc updates
- registry update

Before finishing:
- run relevant tests
- verify docs match behavior
- confirm no unrelated files changed

## Atomic Task Isolation
Implement exactly one workflow contract improvement:
**explicit preflight classification and operator handoff in `run_story.sh`.**

Do not use this story to fix adjacent workflow friction.
If you discover follow-up opportunities, record them in follow-ups instead of extending scope.

## Definition of Success
The workflow must clearly tell the operator:
- why execution is blocked
- whether the block is due to requested-story artifacts or unrelated changes
- exactly what to do next

