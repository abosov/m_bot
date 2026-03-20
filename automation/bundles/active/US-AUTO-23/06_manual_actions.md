# US-AUTO-23: Manual Actions

## Required Human Actions
- Run one real story lifecycle that reaches a normal review/finalize path and inspect the resulting ledger entries.
- Run one story lifecycle that produces a reject or follow-up outcome and confirm the ledger records that outcome clearly.
- Review ledger readability in git diff and confirm it is suitable for future preflight automation.

## Execution Notes
- Preferred verification path:
  - validate the bundle
  - run the story on a feature branch
  - inspect the ledger artifact created or updated under `automation/`
  - confirm start, review, and terminal outcome entries appear as expected
- This story should not be considered complete if the ledger exists only in theory and has not been inspected through at least one realistic lifecycle path.

## Completion Status
- [ ] No manual actions required
- [ ] Manual actions completed and documented