# US-AUTO-51 — Follow-Ups

## Follow-Up Prompt Queue
- `TBD` — Extract a shared helper for manual-finish continuation detection if the final patch duplicates the same predicate across scripts.
- `TBD` — Add a richer operator evidence summary that explicitly prints why a continuation-qualified manual finish is safe.
- `TBD` — Consider whether manual-finish continuation should be recorded explicitly in downstream result artifacts for later auditability.
- `TBD` — After `US-AUTO-28-F1` is merged, assess whether additional operator UX cleanup is still needed or whether the contract is sufficient.

## Iteration Notes
- Keep this story atomic: downstream continuation contract only.
- Do not reopen the rerun-boundary design from US-AUTO-47.
- Do not absorb AI review prompt or normalization work from US-AUTO-50 / US-AUTO-48.
- Do not generalize into descendant-HEAD review semantics outside the manual-finish continuation case.
- If a broader stale-run lifecycle redesign seems desirable, capture it as a separate follow-up rather than widening this story.

