# Manual Actions — US-AUTO-40

## Required Human Actions
Before run:
1. Confirm branch is `feat/us-auto-40-review-artifact-fidelity`.
2. Confirm working tree is clean with `git status --short`.
3. Confirm all active bundle files are populated.
4. Run bundle validation through the normal story runner.

After run:
1. Run `git status --short`.
2. If the only dirt is `M automation/story_change_ledger.jsonl`, run `git restore automation/story_change_ledger.jsonl`.
3. Inspect implementation diff and confirm scope remains aligned with US-AUTO-40.
4. Run targeted tests for touched review/gate files.

Before PR:
1. Confirm approve and reject test paths exist.
2. Confirm docs were updated.
3. Confirm active bundle reflects final implementation.

## Completion Status
Current status: bundle repair required to satisfy validator contract before story execution.

Completion for this story means:
- bundle validates successfully;
- story run completes;
- artifact fidelity enforcement is implemented and tested;
- active bundle reflects the final implemented contract.