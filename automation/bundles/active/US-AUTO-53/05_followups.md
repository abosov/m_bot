## Follow-Up Prompt Queue

1. Resume `US-AUTO-28-F1` only after US-AUTO-53 is merged and `main` is updated locally. Re-run the story from a fresh committed state and use a new run directory.
2. If committed-HEAD diff fidelity still exposes another distinct review-boundary defect, split a new narrow follow-up rather than widening US-AUTO-53.
3. Revisit P2 workflow optimization stories `US-AUTO-29`, `US-AUTO-30`, and `US-AUTO-31` only after the current P1 blocker is cleared.

## Iteration Notes

- This story is intentionally narrower than manual-finish workflow recovery.
- The correct architectural response is to fix the diff comparison contract, not to bypass or soften the gate.
- Registry logic after this bundle:
  - add `US-AUTO-53` as a new P1 follow-up tied to `US-AUTO-28-F1`
  - set `US-AUTO-53` as the next recommended story
  - keep `US-AUTO-28-F1` blocked until this follow-up is implemented and merged
- Estimated delivery profile:
  - Complexity: Medium
  - Risk: Medium
  - Blast Radius: Narrow
- No further split is required at bundle stage because the defect is already isolated to review diff fidelity.
- Main regression risk: accidentally converting true mismatches into false passes.

