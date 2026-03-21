# US-AUTO-24: Follow-Ups

## Follow-Up Prompt Queue
- Draft a dedicated runtime implementation story that applies the approved `US-AUTO-24` contract to the workflow scripts without broadening the design scope.
- `US-AUTO-25` — Loop detection preflight using the redesigned canonical ledger evidence.
- `US-AUTO-26` — Expensive run budget guard once event timing and durability are trustworthy.
- `US-AUTO-27` — Pipeline zone cap after the redesigned evidence contract is implemented.
- `US-AUTO-28` — Escalation gate for loop-risk stories after loop signals and clean-tree semantics are stable.
- `US-AUTO-29` — Targeted test strategy after anti-cycle enforcement semantics stabilize.
- `US-AUTO-30` — Review reuse / cache guard after the redesigned ledger workflow is runtime-enforced.
- `US-AUTO-31` — Post-run checkpoint workflow to reduce immediate rerun loops.

## Iteration Notes
- Do not implement runtime fixes inside this design story.
- If review disputes the chosen durability mechanism, create a separate design correction follow-up instead of partially implementing script changes.
- Keep runtime contract implementation separate from later anti-cycle enforcement so the ledger remains evidence-oriented.
