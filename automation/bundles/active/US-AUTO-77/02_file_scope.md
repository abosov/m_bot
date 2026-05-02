## Story ID and Title

US-AUTO-77 — Operator workflow simplification and decision model

## Files Allowed To Change

docs/90_codex/US_AUTO_OPERATOR_GUIDE.md

Purpose:

- new operator guide;
- documents normal workflow;
- documents analyze command contract;
- documents post-merge registry closure gate;
- documents manual-finish continuation;
- documents dirty tree behavior;
- documents rerun required and rerun forbidden cases;
- documents anti-patterns.

automation/scripts/analyze_story_run.sh

Purpose:

- optional additive operator-facing decision output;
- clarify next action semantics;
- preserve existing output contracts as much as possible;
- do not change rerun, review-stage, classify, or gate safety behavior;
- do not accept run dir as a second positional argument.

tests/test_analyze_story_run.py

Purpose:

- cover new operator decision output;
- cover command-contract guidance if analyze rejects or warns about wrong invocation;
- cover manual-finish continuation guidance if existing fixtures make this practical;
- preserve existing test behavior.

docs/90_codex/README.md

Purpose:

- optional link to docs/90_codex/US_AUTO_OPERATOR_GUIDE.md if the file exists and has a suitable docs index section.

docs/90_codex/epics/US-AUTO_REGISTRY.md

Purpose:

- may be updated only for US-AUTO-77 lifecycle status if required by the workflow;
- do not close US-AUTO-77 before implementation PR is merged;
- do not change unrelated story statuses except if directly required to keep US-AUTO-77 ordering consistent.

## Files Not Allowed To Change

automation/scripts/run_story.sh

automation/scripts/review_story_run.sh

automation/scripts/ai_review_story_run.sh

automation/scripts/classify_review_story_run.sh

automation/scripts/review_gate_story_run.sh

automation/scripts/next_step.sh

Semantic projection producer or consumer internals.

Companion-filter centralization.

Review-fidelity helper refactor.

Stage-loop cap implementation.

Telemetry registry.

Periodic analytics.

Deterministic pytest selection.

Business runtime code.

OAuth scopes.

Database migrations.

Runtime bot behavior.

## Scope Notes

If implementation requires modifying files outside the allowed list, stop and explain why.

If next_step.sh appears necessary, do not implement it in this story unless the change is tiny and purely additive. Prefer adding it as a follow-up story.

If a registry status update is needed, keep it minimal and specific to US-AUTO-77.

If tests fail, fix implementation. Do not weaken tests to pass.

