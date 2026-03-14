# US-AUTO-13: Story Finalization Script

## Story ID and Title
- Story ID: `US-AUTO-13`
- Title: `Story Finalization Script`

## Objective
Add a deterministic finalization script that completes the post-implementation workflow for a story through GitHub CLI, including PR resolution checks, merge execution, local main resync, and branch cleanup.

## Scope
- Add `automation/scripts/finalize_story.sh`.
- Implement CLI-driven finalization using `gh`.
- Require clean working tree before finalization.
- Require current branch to be a non-main story branch.
- Detect the story PR for the current branch or accept an explicit PR number.
- Verify PR checks are green before merge.
- Perform squash merge through `gh`.
- Ensure local repository ends on updated `main`.
- Ensure local and remote story branches are deleted.
- Add focused tests for finalization script behavior.
- Update workflow docs/checklists.

## Non-goals
- Do not implement allowed-files guard.
- Do not implement AI review gate.
- Do not redesign `run_story.sh` or `run_codex_task.sh`.
- Do not change bundle materialization logic.
- Do not add background waiting or polling daemons.

## Dependencies
- Existing bundle materialization/validation flow.
- Existing GitHub CLI (`gh`) workflow.
- Existing story execution checklist.
- Existing PR-based merge workflow.

## Source of Truth
- `automation/scripts/run_story.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `automation/bundles/active/US-AUTO-13/`
- current GitHub CLI merge workflow used in completed stories

## Current Code Reality
- Story execution and review are already scripted, but final PR creation/merge/final cleanup still require manual command orchestration.
- The project already uses `gh` successfully for PR creation, checks, and merge.
- Workflow rules require no stale story branches after merge and require returning to updated `main`.

## Target Outcome
- One script finalizes a story safely through `gh`.
- Finalization fails fast on dirty tree, wrong branch, missing PR, or failing checks.
- Successful finalization leaves the repo on clean updated `main`.
- Successful finalization removes story branches locally and remotely.

## Allowed Files
- `automation/scripts/finalize_story.sh`
- `tests/test_finalize_story_script.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `automation/bundle_packs/US-AUTO-13.bundle.md`
- `automation/bundles/active/US-AUTO-13/**`

## Forbidden Files
- `automation/run_codex_task.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `backend/**`
- `frontend/**`
- `database/**`
- `migrations/**`

## Risks
- Overcoupling to one very specific `gh` output format.
- Accidentally allowing finalize on dirty tree or `main`.
- Incomplete cleanup verification after merge.

## Manual Actions
- Review the finalization safety checks carefully.
- Manually inspect one finalized story after script-based merge.

## Acceptance Notes
- Finalization must fail on dirty tree.
- Finalization must fail on `main`.
- Finalization must fail when PR checks are not green.
- Successful finalization must land on updated clean `main`.
- Successful finalization must delete local and remote story branches.

