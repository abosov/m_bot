## Story ID and Title

US-AUTO-60 — Implementation freeze and review-evidence refresh without Codex rerun

## Follow-Up Prompt Queue

Candidate 1: US-AUTO-58 — Stage-loop cap and forced escalation threshold.

Purpose:

- add explicit loop cap after repeated run/rerun/manual-finish/review-stage cycles;
- force escalation instead of allowing repeated non-converging loops;
- use US-AUTO-60 freeze/refresh path as one of the allowed exits.

Reason to defer:

- US-AUTO-60 must first create the safe freeze/refresh primitive.

Candidate 2: US-AUTO-31 — Mandatory analyze gate before rerun or next phase.

Purpose:

- enforce that the operator cannot safely proceed to rerun, review, classify, or gate without an analyze decision;
- convert US-AUTO-77 guide rules into technical enforcement.

Reason to defer:

- the analyzer must first understand the US-AUTO-60 refresh state.

Candidate 3: US-AUTO-74 — Centralize semantic projection and companion-filter contract.

Purpose:

- remove duplicated semantic projection / companion-filter / review-fidelity logic from analyze/review/ai_review/classify/gate flows;
- reduce maintainability drift.

Reason to defer:

- current blocker is operational convergence, not semantic centralization;
- US-AUTO-74 should resume after US-AUTO-60/58/31 or explicit parking.

Candidate 4: US-AUTO-30 — Safe review-artifact reuse eligibility.

Purpose:

- generalize safe reuse of review artifacts when deterministic eligibility can be proven.

Reason to defer:

- US-dles an explicit implementation-freeze refresh path, not a broad cache/reuse policy.

Candidate 5: US-AUTO-29 — Deterministic story-scoped verification strategy.

Purpose:

- reduce validation cost by selecting minimal required pytest scope.

Reason to defer:

- refresh evidence and loop control are higher priority.

Candidate 6: US-AUTO-61/62/63 — Workflow telemetry and analytics.

Purpose:

- record refresh usage, repeated loops, manual interventions, timings, and automation opportunities.

Reason to defer:

- telemetry should observe stabilized workflow states after freeze/refresh and loop cap are implemented.

## Iteration Notes

Tag these as future automation and operator UX improvements:

- command that prints latest valid refresh run for a story;
- structured report comparing source run, refreshed evidence, and current HEAD;
- automatic detection that no-Codex refresh is the preferred action after accepted implementation;
- UI summary showing why rerun is not needed or forbidden;
- telemetry event for `implementation_freeze_requested`;
- telemetry event for `review_evidence_refreshed`;
- escalation after repeated stale refresh attempts.

Do not add these to US-AUTO-60 unless required for minimal correctness.

## Parking Rules

Do not resume US-AUTO-74 until US-AUTO-60, US-AUTO-58, and US-AUTO-31 are implemented or explicitly parked.

Do not start business features until the freeze/loop/analyze-gate line is resolved or consciously accepted as safe enough.

