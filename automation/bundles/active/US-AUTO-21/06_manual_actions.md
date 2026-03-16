# US-AUTO-21: Manual Actions

## Required Human Actions
- Review the fail-fast message in a synthetic dirty-working-tree scenario.
- Confirm the operator guidance matches the intended local workflow.

## Execution Notes
- Test once with a clean tree and confirm review/gate still works.
- Test once with a dirty tree after a successful materialized run and confirm gate blocks before AI review starts.

## Completion Status
- [ ] No manual actions required
- [ ] Manual actions completed and documented
