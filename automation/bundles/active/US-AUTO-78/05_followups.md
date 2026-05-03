## Follow-Up Prompt Queue

### US-AUTO-58

Implement stage-loop cap and forced escalation threshold across run/rerun/refresh/review/classify/fix loops.

This follow-up should explicitly account for the US-AUTO-60 refresh path so that the pipeline does not enter a new loop form:

`refresh -> review -> reject -> small fix -> amend -> refresh`

### US-AUTO-31

Make analyze the mandatory decision gate before rerun, refresh, review continuation, classification, gate, escalation, follow-up, or phase advance.

This follow-up may introduce or formalize a machine-readable `operator_decision.json` artifact if that is the cleanest way to support future orchestration.

### US-AUTO-79

Add a story pipeline orchestrator that executes deterministic safe next steps automatically.

Likely script name:

`automation/scripts/advance_story.sh`

The orchestrator should read the analyze decision output and continue only while the next action is deterministic and safe.

### US-AUTO-80

Add compact operator/AI decision packet UX for non-deterministic stops.

This may be folded into US-AUTO-79 if the implementation is small and atomic.

### US-AUTO-74

Resume semantic projection and companion-filter centralization only after US-AUTO-58, US-AUTO-31, and the orchestration decision model are resolved or explicitly parked.

## Iteration Notes

US-AUTO-78 exists because US-AUTO-60 changed the strategic state of the pipeline.

Before US-AUTO-60, the next blocker was the absence of implementation freeze and no-Codex review-evidence refresh.

After US-AUTO-60, that blocker is closed. The next work should focus on stage-loop control, mandatory analyze-gate enforcement, deterministic orchestration, and compact decision packet UX before resuming US-AUTO-74 maintainability cleanup or the US-AUTO-61/62 observability line.

