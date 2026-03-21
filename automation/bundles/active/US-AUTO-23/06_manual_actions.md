# US-AUTO-23: Manual Actions

## Required Human Actions
- Run one real story lifecycle that reaches a normal review/finalize path and inspect `automation/story_change_ledger.jsonl`.
- Run one story lifecycle that produces a reject outcome and confirm `review_outcome` + `story_rejected` entries are appended.
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

## Additional Manual Verification

- Verify `automation/story_change_ledger.jsonl` is normalized before merge:
  - no bootstrap-only residue
  - no duplicate lifecycle entries caused by local retries
  - no workstation-specific absolute paths
- Verify each newly written ledger entry is valid JSON on a single line and can be parsed with standard JSON tooling.
- Verify a realistic lifecycle path writes canonical append-only evidence for the intended event sequence.
- Verify the operator commits the workflow state containing the relevant ledger update before treating the ledger as durable downstream evidence.
