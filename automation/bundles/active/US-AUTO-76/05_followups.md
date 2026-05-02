## Follow-Up Prompt Queue

Potential follow-up after US-AUTO-76:

1. US-AUTO-77 — Operator workflow simplification and decision model.
2. US-AUTO-74 — Centralize semantic projection and companion-filter contract.
3. US-AUTO-31 — Mandatory analyze gate before rerun or next phase.
4. US-AUTO-58 — Stage-loop cap and forced escalation threshold.

Do not start US-AUTO-77 until US-AUTO-76 is resolved or explicitly parked.

Do not start US-AUTO-74 until US-AUTO-76 and US-AUTO-77 are resolved or explicitly parked.

Do not revive US-AUTO-28 until US-AUTO-76, US-AUTO-77, and US-AUTO-58 clarify classifier semantics, operator decision flow, and stage-loop policy.

Do not revive US-AUTO-57 or US-AUTO-69 unless a concrete residual defect is revalidated.

## Iteration Notes

If classifier changes become broader than governance artifact semantics, stop and split the work.

If review-gate changes require touching analyze, ai_review, or review_story scripts, stop and reassess. That is likely US-AUTO-74 or another follow-up, not US-AUTO-76.

If operator-facing simplification becomes necessary, park it for US-AUTO-77.

If duplicated helper logic becomes painful during implementation, do not centralize in this story. Add a note for US-AUTO-74 instead.

If tests reveal that existing behavior is ambiguous, preserve fail-closed behavior for unknown or wrong-story paths.

If the classifier still rejects approved governance artifacts after implementation, collect the exact changed-file list and classifier output, then refine only the governance artifact classification logic.

