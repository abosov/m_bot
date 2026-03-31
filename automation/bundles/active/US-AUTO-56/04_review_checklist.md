## Scope Validation
- APPROVE only if changed files are limited to the allowed scope
- REJECT if any review/gate/classify/AI-review script changed
- REJECT if any new file or telemetry artifact was introduced
- REJECT if the implementation adds rerun-skip, loop-cap, reuse, telemetry, or verification-selection behavior
- REJECT if the registry update claims more than bundle/implementation lifecycle progress for US-AUTO-56

## Functional Validation
- APPROVE only if stage-gate guidance is explicit and deterministic
- APPROVE only if output clearly distinguishes:
  - review-stage allowed
  - commit/discard required before review-stage
  - manual-finish continuation active and rerun forbidden
- REJECT if guidance weakens or contradicts existing fail-closed workflow contracts
- REJECT if the implementation changes policy instead of clarifying existing policy
- REJECT if manual-finish wording allows another rerun before manual finish is complete

## Verification
- APPROVE only if targeted automated tests cover the intended guidance states
- REJECT if tests are missing for dirty-tree review blocking
- REJECT if tests are missing for manual-finish rerun prohibition guidance
- REJECT if tests rely only on vague substring matches that do not prove the stage-gate meaning
- Final result must be binary: APPROVE or REJECT with no soft-pass language

