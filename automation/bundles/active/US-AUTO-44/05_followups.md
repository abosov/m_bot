# US-AUTO-44: Follow-Ups

## Follow-Up Prompt Queue

### FOLLOW-UP 1
FINDING:
Review/gate stage currently recomputes review/classification, allowing decision drift after an explicit approve path.

INTENT:
Ensure `review_gate_story_run.sh` consumes existing review/classification artifacts instead of silently recomputing them.

SCOPE:
- `automation/scripts/review_gate_story_run.sh`

OUT_OF_SCOPE:
- `run_story.sh`
- bundle spec changes
- unrelated workflow scripts

### FOLLOW-UP 2
FINDING:
No reverse synchronization from active bundle to bundle pack leads to bundle-pack drift and packed-artifact fidelity failures.

INTENT:
Introduce deterministic rebuild of bundle pack from the active bundle.

SCOPE:
- bundle tooling for active -> pack sync

OUT_OF_SCOPE:
- `run_story.sh`
- validator logic
- review/gate logic

## Iteration Notes
- Keep US-AUTO-44 focused on preflight classification and operator handoff only.
- Do not expand this story into review/gate redesign.
- Do not expand this story into reverse bundle synchronization tooling.
- Any additional workflow integrity issues discovered during execution should be captured as follow-up stories, not implemented here.

## Deferred Questions
- Should review_gate be strictly artifact-consuming with no reclassification side effects?
- Should bundle tooling support deterministic active-to-pack rebuild as a first-class command?