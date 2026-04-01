## Follow-Up Prompt Queue
- US-AUTO-31 — mandatory analyze gate before rerun or next phase
- US-AUTO-58 — stage-loop cap and forced escalation threshold
- US-AUTO-60 — lightweight review-evidence refresh without full rerun
- US-AUTO-30 — safe review-artifact reuse eligibility
- US-AUTO-61 — workflow telemetry registry for run stages, blockers, manual interventions, and timings

## Iteration Notes
- This story intentionally addresses only early rerun prevention, not later-stage decision enforcement.
- If implementation pressure suggests changing analyze semantics or stage-loop behavior, stop and leave that work to the follow-up stories above.
- Keep the proof rule conservative and narrowly tied to existing committed-head evidence.
- Registry logic to apply after successful bundle preparation:
  - selected next story remains `US-AUTO-57`
  - status should become `Bundle Drafted`
  - `US-AUTO-56` remains closed as `Implemented`
- No additional decomposition is required because the current story remains atomic.

