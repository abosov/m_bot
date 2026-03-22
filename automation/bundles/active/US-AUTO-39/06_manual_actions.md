# US-AUTO-39: Manual Actions

## Required Human Actions
- Materialize the bundle after pack edits.
- Validate the active bundle before execution.
- Run targeted tests for finalize/review/gate behavior.
- Simulate a flow where finalize mutates HEAD after initial approval.
- Verify stale approval is rejected and re-review/re-gate on finalized HEAD restores readiness.
- Inspect `review_gate_result.json` to confirm it records both reviewed HEAD and current checkout HEAD.

## Completion Status
- [ ] Bundle materialized
- [ ] Bundle validated
- [ ] Manual verification completed
- [ ] Ready for PR
