# Follow-ups — US-AUTO-44

## FOLLOW-UP 1

FINDING:
Review/gate stage currently recomputes review/classification, allowing decision drift.

INTENT:
Ensure review_gate consumes existing artifacts instead of recomputing them.

SCOPE:
- `automation/scripts/review_gate_story_run.sh`

OUT_OF_SCOPE:
- run_story logic
- bundle spec changes

---

## FOLLOW-UP 2

FINDING:
No reverse synchronization from active bundle to bundle pack leads to artifact drift.

INTENT:
Introduce deterministic rebuild of bundle pack from active bundle.

SCOPE:
- new script or extension to bundle tooling

OUT_OF_SCOPE:
- run_story logic
- validator logic