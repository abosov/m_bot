# Follow-Ups — US-AUTO-49

## Follow-Up Prompt Queue
1. **US-AUTO-28-F1 rerun after unblock**
   - Preconditions:
     - `US-AUTO-49` merged to `main`
     - working tree clean
     - latest run directory for `US-AUTO-49` analyzed and resolved
   - Intent:
     - rerun `US-AUTO-28-F1` now that false scope rejection from committed bundle artifacts is removed

2. **Optional future hardening if needed**
   - Only if evidence shows additional provenance edge cases not covered by this fix
   - Must remain a separate atomic story and not be folded into `US-AUTO-49`

## Iteration Notes
- `US-AUTO-49` is intentionally atomic and should not absorb `US-AUTO-28-F1` logic.
- Registry logic for this iteration:
  - `US-AUTO-49` becomes the active blocker-follow-up
  - `US-AUTO-28-F1` remains blocked by the scope-baseline contract until `US-AUTO-49` is merged
- This story exists to restore pipeline consistency, not to redesign the full orchestration model.

