# US-AUTO-13 PROMPT 1 — Story Finalization Script

## Role
You are the Zumbot workflow automation engineer working under the repository's CODEX Operating System.

## Story
US-AUTO-13 — Story Finalization Script.

## Goal
Add a deterministic finalization script that completes the post-implementation workflow for a story through GitHub CLI, including PR resolution checks, merge execution, local main resync, and branch cleanup.

## Source of Truth
- `do0_codex/STORY_EXECUTION_CHECKLIST.md`
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
Update workflow docs/checklists to describe scripted finalization through `gh`.

## Output
Return:
1. changed files summary
2. design rationale
3. validation performed
4. risks / follow-ups
5. final diff

