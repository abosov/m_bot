## Story ID and Title

US-AUTO-77 — Operator workflow simplification and decision model

## Source of Truth

Primary registry:

- docs/90_codex/epics/US-AUTO_REGISTRY.md

Current story bundle pack:

- automation/bundle_packs/US-AUTO-77.bundle.md

Materialized active bundle:

- automation/bundles/active/US-AUTO-77/

Operator guide to create:

- docs/90_codex/US_AUTO_OPERATOR_GUIDE.md

Relevant scripts:

- automation/scripts/run_story.sh
- automation/scripts/analyze_story_run.sh
- automation/scripts/review_story_run.sh
- automation/scripts/ai_review_story_run.sh
- automation/scripts/classify_review_story_run.sh
- automation/scripts/review_gate_story_run.sh

## Current Code Reality

The US-AUTO milestone goal is to make the AI-dev pipeline safe enough to return to business features without constant manual pipeline debugging.

US-AUTO-75 introduced semantic projection and review-fidelity support.

US-AUTO-76 fixed classifier/review gate semantics so approved governance/story artifacts can be accepted when explicitly scoped.

The remaining blocker is operational complexity.

The operator still needs to understand too much internal state:

- rerun;
- analyze;
- manual finish;
- review-stage;
- ai_review;
- classify;
- gate;
- registry closeout;
- dirty tree gate;
- stale AUTOMATION_RUN_DIR invalidation;
- committed HEAD alignment.

US-AUTO-77 should simplify the operator decision model without weakening safety.

Known concrete issue:

The wrong analyze command shape is:

automation/scripts/analyze_story_run.sh US-AUTO-77 automation/runs/US-AUTO-77/<RUN_DIR>

The correct analyze command shape is:

AUTOMATION_RUN_DIR=automation/runs/US-AUTO-77/<RUN_DIR> automation/scripts/analyze_story_run.sh US-AUTO-77

## Architectural Intent

The implementation should be guide-first and additive.

The operator guide should become the stable human-facing contract for running stories.

If automation/scripts/analyze_story_run.sh is modified, the change should add clearer operator-facing decision output without changing safety semantics.

The desired mental model is:

1. Operator runs story.
2. Operator runs analyze with AUTOMATION_RUN_DIR.
3. Operator reads one decision section.
4. Operator follows allowed next action.
5. Operator avoids explicitly forbidden actions.
6. Operator closes the story only after PR merge, cleanup, main update, and registry closeout.

The operator should not have to infer the correct next step from conflicting raw status lines.

## Risks

Main risk:

- accidentally changing pipeline semantics while trying to simplify UX.

Specific risks:

- weakening dirty tree review-stage gate;
- allowing stale AUTOMATION_RUN_DIR after a new commit;
- making rerun optional when existing logic requires it;
- making review-stage allowed when existing logic blocks it;
- accepting run dir as a second positional argument to analyze_story_run.sh;
- mixing US-AUTO-77 with US-AUTO-74 semantic projection centralization;
- hiding manual-finish complexity rather than documenting it;
- treating PR merge as story closure without registry closeout.

Mitigations:

- create operator guide first;
- make analyze output additive only;
- preserve existing tests;
- add targeted tests for output additions;
- do not modify semantic projection or review gate behavior;
- keep next_step.sh as a follow-up unless trivial.

## Acceptance Notes

The story should be accepted if it creates a clear operator guide and optionally improves analyze output in a narrow, tested, additive way.

The story should be rejected if it changes semantic projection behavior, rewrites classifier semantics, weakens safety gates, or expands into telemetry/stage-loop/test-optimization work.

The guide must include the post-merge registry closure gate:

PR merged is not story closed.

Story closed requires:

1. PR merged.
2. Branch cleanup done.
3. main updated locally.
4. registry checked.
5. registry updated or explicitly confirmed not required.

