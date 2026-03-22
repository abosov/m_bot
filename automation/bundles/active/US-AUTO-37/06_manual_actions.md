# US-AUTO-37: Manual Actions

## Required Human Actions
- Review the updated bundle pack and confirm placeholders are fully resolved.
- Materialize the bundle.
- Validate the materialized bundle.
- Run the story after validation succeeds.
- Review `git status` after run and finalize while this story is being implemented.

## Suggested Manual Verification
- Confirm `automation/story_change_ledger.jsonl` no longer causes happy-path dirty state.
- Confirm real implementation changes are still visible to workflow checks.
- Review focused tests and final diff before PR.

## Completion Status
- [ ] Bundle placeholders resolved
- [ ] Bundle materialized
- [ ] Bundle validated
- [ ] Manual verification completed
- [ ] Ready for implementation
