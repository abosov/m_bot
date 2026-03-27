# Context Bundle

## Source of Truth
- run_story.sh escalation logic
- US-AUTO-28 anti-cycle enforcement

## Current Code Reality
- escalation artifact not strictly validated
- possible acceptance of malformed or spoofed inputs

## Architectural Intent
- escalation must be deterministic and tamper-resistant
- validation must precede any decision
- pipeline must operate in fail-closed mode

## Risks
- escalation bypass via artifact manipulation
- inconsistent behavior across runs

## Acceptance Notes
- strict schema validation enforced
- no implicit trust of artifacts

---

