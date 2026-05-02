## Story ID and Title

US-AUTO-77 — Operator workflow simplification and decision model

## Follow-Up Prompt Queue

Candidate 1: next_step.sh operator command router.

Purpose:

- provide a single command that reads latest analyze output and prints only the next safe operator action;
- must not bypass analyze;
- must not weaken review-stage gates;
- must not hide dirty tree;
- must not run actions automatically unless explicitly designed later.

Reason to defer:

- this may require new state-machine logic;
- US-AUTO-77 should stay focused on guide and additive analyze output.

Candidate 2: US-AUTO-31 — Mandatory analyze gate before rerun or next phase.

Purpose:

- enforce analyze before rerun or review-stage;
- convert the operator guide rule into a technical gate.

Reason to defer:

- US-AUTO-77 first documents the decision model;
- US-AUTO-31 can implement enforcement after the model is stable.

Candidate 3: US-AUTO-58 — Stage-loop cap and forced escalation threshold.

Purpose:

- prevent repeated non-converging run/rerun/manual-finish loops;
- escalate after a defined threshold.

Reason to defer:

- needs the operator model from US-AUTO-77;
- should not be mixed into guide/output cleanup.

Candidate 4: US-AUTO-61, US-AUTO-62, US-AUTO-63 — workflow telemetry and analytics.

Purpose:

- record workflow events;
- capture manual operator decisions;
- identify automation opportunities;
- report recurring friction.

Reason to defer:

- events should be modeled after the operator workflow is stabilized.

Candidate 5: US-AUTO-60 and US-AUTO-30 — lightweight review-evidence refresh and safe artifact reuse.

Purpose:

- reduce full rerun cost when safe;
- reuse review artifacts when deterministic eligibility is proven.

Reason to defer:

- cost optimization should come after safe operator workflow.

Candidate 6: US-AUTO-29 — deterministic story-scoped verification.

Purpose:

- select minimal required pytest scope for a story.

Reason to defer:

- important but lower priority than operator correctness and clarity.

## Iteration Notes

Tag the following as future operator UX improvements:

- conflicting analyze output;
- blocked_non_converging_rerun with clean committed-head pytest pass;
- manual-finish empty commit requirement;
- stale AUTOMATION_RUN_DIR after commit;
- ledger-only dirty tree cleanup;
- registry closeout after merge;
- wrong analyze positional argument usage.

Do not create follow-up tasks for business features until US-AUTO-77 is resolved and registry closure is done.

Do not resume US-AUTO-74 until US-AUTO-77 is resolved or explicitly parked.

