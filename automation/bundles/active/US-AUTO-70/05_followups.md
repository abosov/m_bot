## Follow-Up Prompt Queue
- Revisit US-AUTO-69 only if US-AUTO-70 uncovers a still-residual coupling beyond rerun-preflight recomputation.
- Consider a later optimization story only after US-AUTO-70 lands and proves that the effective filtered review surface can be recomputed deterministically within `run_story.sh`.
- Do not open safe-reuse, telemetry, or UX follow-ups from this story unless a separate committed observation requires them.

## Iteration Notes
US-AUTO-70 is intentionally atomic and should remain so. If implementation pressure suggests changing `run_codex_task.sh` or any review-stage script, that is evidence of a new story, not permission to widen this one.

Completion of US-AUTO-70 is the explicit return condition recorded for the parked split line of US-AUTO-69.

