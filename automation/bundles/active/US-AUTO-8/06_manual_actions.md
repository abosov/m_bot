# US-AUTO-8 Manual Actions

## Before implementation
- Confirm branch is correct
- Keep patch limited to automation workflow files

## After implementation
Run manual checks:

1. execute the story run workflow
2. confirm the primary working tree remains clean after the run
3. inspect latest run artifacts under `automation/runs/US-AUTO-8/<RUN_ID>/`
4. verify manifest contains worktree metadata
5. verify temporary worktree cleanup happened

## Merge guidance
Do not merge until:
- isolated execution is confirmed
- tests pass
- no orphaned worktree remains after normal completion
- artifact generation still works as expected
