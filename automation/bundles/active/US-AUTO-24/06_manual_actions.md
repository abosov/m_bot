# US-AUTO-24: Manual Actions

## Required Human Actions
- Review the event model and confirm that each event is assigned to exactly one workflow state.
- Confirm the chosen durability definition matches how operators actually share reviewed history.
- Confirm the recommended sequencing does not require review artifacts to be regenerated after a ledger-only commit.
- Confirm the clean-tree recommendation still blocks arbitrary pre-existing ledger edits.
- Use the approved design as the prerequisite when drafting the runtime implementation follow-up.

## Execution Notes
- This story is complete when the design bundle is internally consistent and reviewable; no runtime script execution is required in this prompt.
- Reviewers should explicitly test the design against both a normal approve path and a reject/follow-up path to ensure the same contract holds.
- If operators need a different branch/merge sequence than the recommendation, capture that as a separate design follow-up before implementation.

## Completion Status
- [ ] No manual actions required
- [ ] Manual actions completed and documented
