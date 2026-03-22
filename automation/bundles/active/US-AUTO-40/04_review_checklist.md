# Review Checklist — US-AUTO-40

## Scope Validation
- Are changes confined to review/gate workflow, tests, and focused docs?
- Does the implementation avoid drifting into US-AUTO-41, US-AUTO-37, US-AUTO-38, US-AUTO-35, or US-AUTO-36?
- Are changed files explainable by the artifact-fidelity goal?

## Functional Validation
- Is there now a clearly defined authoritative diff for review?
- Does review and/or gate detect stale or incomplete artifact state?
- Does mismatch fail closed or produce explicit reject?
- Does faithful artifact state still allow normal approval?
- Does US-AUTO-39 HEAD-binding behavior remain intact?

## Verification
- Are automated tests present for approve and reject paths?
- Are failure modes deterministic and operator-visible?
- Do docs explain the fidelity invariant and rerun/remediation behavior?
- Does the active bundle reflect the final implemented contract?