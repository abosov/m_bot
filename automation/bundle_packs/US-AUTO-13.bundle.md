# Story Bundle Pack
Story-ID: US-AUTO-13
Version: 1

=== FILE: 00_story.md ===
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
- There is no dedicated finalization script yet, so merge, resync, and cleanup are easy to apply inconsistently.

## Target Outcome
- One script finalizes a story safely through `gh`.
- Finalization fails fast on dirty tree, wrong branch, missing PR, or failing checks.
- Successful finalization leaves the repo on clean updated `main`.
- Successful finalization removes story branches locally and remotely.
- The checklist documents `automation/scripts/finalize_story.sh` as the default post-implementation merge path.

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

=== FILE: 01_context_bundle.md ===
# US-AUTO-13: Context Bundle

## Source of Truth
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- current `gh`-based story merge workflow already used in the repo
- project rule: after merge, switch to `main`, pull latest `main`, and delete local/remote working branches

## Current Code Reality
- Story execution is already automated through bundle materialization, validation, and runner scripts.
- PR creation and merge are currently performed via manual `gh` commands in the terminal.
- Final branch cleanup is currently manual discipline, not an enforced scripted workflow.

## Architectural Intent
- Add one explicit finalization layer after story implementation and PR readiness.
- Keep finalization separate from story execution and review scripts.
- Make `gh` the canonical integration point for GitHub operations.

## Risks
- GitHub network/transient failures can interrupt finalize flow.
- Parsing CLI output too loosely could hide real failures.

## Acceptance Notes
- Scripted finalization must be deterministic and fail fast.
- Finalization must preserve the project's no-stale-branches rule.

=== FILE: 02_file_scope.md ===
# US-AUTO-13: File Scope

## Files Allowed To Change
- `automation/scripts/finalize_story.sh`
- `tests/test_finalize_story_script.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `automation/bundle_packs/US-AUTO-13.bundle.md`
- `automation/bundles/active/US-AUTO-13/**`

## Files Not Allowed To Change
- `automation/run_codex_task.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `backend/**`
- `frontend/**`
- `database/**`
- `migrations/**`

## Scope Notes
- Keep the script deterministic and CLI-oriented.
- Use `gh` as the default and preferred GitHub integration path.
- Do not mix in scope guard or review gate logic.

=== FILE: 03_master_prompt.md ===
# US-AUTO-13 PROMPT 1 — Story Finalization Script

## Role
You are the Zumbot workflow automation engineer working under the repository's CODEX Operating System.

## Story
US-AUTO-13 — Story Finalization Script.

## Goal
Add a deterministic finalization script that completes the post-implementation workflow for a story through GitHub CLI, including PR resolution checks, merge execution, local main resync, and branch cleanup.

## Source of Truth
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- current `gh`-based merge workflow used in completed stories
- `automation/bundles/active/US-AUTO-13/00_story.md`
- `automation/bundles/active/US-AUTO-13/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-13/02_file_scope.md`

## Files Allowed To Change
- `automation/scripts/finalize_story.sh`
- `tests/test_finalize_story_script.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `automation/bundle_packs/US-AUTO-13.bundle.md`
- `automation/bundles/active/US-AUTO-13/**`

## Files Not Allowed To Change
- `automation/run_codex_task.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `backend/**`
- `frontend/**`
- `database/**`
- `migrations/**`

## Implementation Requirements
1. Add `automation/scripts/finalize_story.sh`.
2. Require clean working tree before finalization.
3. Refuse to run on `main`.
4. Detect or accept the PR to finalize.
5. Verify PR checks are green before merge.
6. Perform squash merge via `gh`.
7. Ensure local checkout ends on `main`.
8. Pull latest `main` with `--ff-only`.
9. Ensure local and remote story branches are deleted.
10. Keep design simple and CLI-oriented.

## Testing
Add or update focused tests that verify:
- dirty tree is rejected
- main branch is rejected
- successful finalize path calls expected commands
- failed checks block merge

## Documentation
Update workflow docs/checklists to describe `automation/scripts/finalize_story.sh` as the scripted finalization path through `gh`.

## Output
Return:
1. changed files summary
2. design rationale
3. validation performed
4. risks / follow-ups
5. final diff

=== FILE: 04_review_checklist.md ===
# US-AUTO-13: Review Checklist

## Scope Validation
- [ ] Changes stay inside `02_file_scope.md`
- [ ] No allowed-files guard logic was added
- [ ] No AI review gate logic was added
- [ ] No unrelated runner refactor was introduced

## Functional Validation
- [ ] Dirty tree is blocked
- [ ] `main` branch is blocked
- [ ] Non-green PR checks block merge
- [ ] Successful finalize lands on updated clean `main`
- [ ] Successful finalize removes story branches locally and remotely

## Architecture Validation
- [ ] Finalization is a separate workflow layer from story execution
- [ ] `gh` is used as the canonical GitHub integration path
- [ ] Finalization logic is deterministic and explicit

## Verification
- [ ] Focused tests updated
- [ ] Docs/checklist updated
- [ ] Follow-ups captured separately

=== FILE: 05_followups.md ===
# US-AUTO-13: Follow-Ups

## Follow-Up Prompt Queue
- `US-AUTO-14` — Allowed Files Guard
- `US-AUTO-15` — AI Review Gate
- `US-AUTO-16` — Runner Progress Telemetry

## Iteration Notes
- Keep this story focused on finalization only.
- Do not mix in review gating or scope enforcement.
- Keep the script deterministic and fail fast instead of polling for checks.

=== FILE: 06_manual_actions.md ===
# US-AUTO-13: Manual Actions

## Required Human Actions
- Run one scripted finalize flow on a real story branch.
- Inspect final branch state after scripted merge.
- Review CLI failure messages for clarity.

## Execution Notes
- GitHub CLI (`gh`) is the default preferred path for GitHub automation in this project.

## Completion Status
- [ ] No manual actions required
- [ ] Manual actions completed and documented
