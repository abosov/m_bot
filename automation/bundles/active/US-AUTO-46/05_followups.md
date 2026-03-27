# US-AUTO-46: Follow-Ups

## Follow-Up Prompt Queue
- `TBD` — Reuse the same dirty-path classification helper as run preflight if the implementation duplicates logic
- `TBD` — Refine review-boundary false positives if explicitly ephemeral runtime-only artifacts create operator friction

## Iteration Notes
- Keep this story focused on committed-HEAD review fidelity only.
- Do not mix in runner redesign, gate redesign, or auto-commit behavior.
- If implementation discovers a need for helper extraction or broader clean-tree policy refinement, capture it as a separate follow-up rather than widening this story.
- Each future follow-up prompt must remain atomic, independently reviewable, and limited to one finding or blocker.

