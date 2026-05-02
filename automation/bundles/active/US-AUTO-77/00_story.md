## Story ID and Title

US-AUTO-77 — Operator workflow simplification and decision model

## Objective

Add an operator workflow layer that reduces cognitive and operational complexity without weakening committed-HEAD, pinned-run, rerun, review, classify, or gate safety invariants.

The operator should be able to follow a clear path:

run_story → analyze → operator decision → review/classify/gate/manual-finish/stop

Instead of manually reconciling raw pipeline signals such as RUN STATUS, Next recommended command, Review-stage, Rerun gate, manual-finish continuation, dirty tree state, stale AUTOMATION_RUN_DIR invalidation, committed HEAD alignment, and registry closeout state.

## Scope

In scope:

- create docs/90_codex/US_AUTO_OPERATOR_GUIDE.md;
- document normal operator workflow;
- document pre-story gate;
- document correct analyze_story_run.sh command contract;
- document dirty tree handling;
- document rerun required cases;
- document rerun forbidden cases;
- document manual-finish continuation;
- document review-stage path;
- document ai_review, classification, and review gate path;
- document post-merge registry closure gate;
- document anti-patterns;
- optionally add additive operator-facing decision output to automation/scripts/analyze_story_run.sh;
- add or update tests in tests/test_analyze_story_run.py for the added operator output.

The correct analyze command contract must be documented as:

AUTOMATION_RUN_DIR=automation/runs/<STORY_ID>/<RUN_DIR> automation/scripts/analyze_story_run.sh <STORY_ID>

The wrong form must be explicitly documented as an anti-pattern:

automation/scripts/analyze_story_run.sh <STORY_ID> automation/runs/<STORY_ID>/<RUN_DIR>

## Non-goals

Do not centralize semantic projection logic in this story.

Do not refactor companion-filter implementation.

Do not change semantic_projection.json producer or consumer behavior.

Do not implement stage-loop cap logic.

Do not implement workflow telemetry.

Do not implement deterministic story-scoped pytest selection.

Do not introduce business features.

Do not broaden GitHub, OAuth, calendar, or external service scopes.

Do not change tests to hide regressions.

Do not weaken fail-closed behavior.

Do not replace existing review, classify, or gate scripts.

Do not introduce a large next_step.sh automation. If next_step.sh would require new state-machine logic, document it as a follow-up instead.

## Dependencies

US-AUTO-75 must be merged.

US-AUTO-76 must be merged and closed in registry.

US-AUTO-74 must remain parked until US-AUTO-77 is resolved or explicitly parked.

## Source of Truth

Primary source of truth:

- docs/90_codex/epics/US-AUTO_REGISTRY.md

Required new operator guide:

- docs/90_codex/US_AUTO_OPERATOR_GUIDE.md

Existing scripts whose behavior and output must be respected:

- automation/scripts/run_story.sh
- automation/scripts/analyze_story_run.sh
- automation/scripts/review_story_run.sh
- automation/scripts/ai_review_story_run.sh
- automation/scripts/classify_review_story_run.sh
- automation/scripts/review_gate_story_run.sh

## Current Code Reality

After US-AUTO-76, classifier and review gate allow explicitly scope-approved governance artifacts for the active story while still rejecting wrong-story governance artifacts.

However, operator workflow remains cognitively difficult.

Known friction from US-AUTO-76:

- analyze command was easy to run incorrectly by passing the run directory as a second positional argument;
- correct command passes run dir through AUTOMATION_RUN_DIR;
- analyze output may contain mixed signals, for example blocked run status while review-stage is allowed;
- manual-finish continuation is correct but operator-unfriendly;
- run_story.sh after a manual-finish boundary can be the wrong action;
- dirty tree must block review-stage;
- PR merged does not mean story closed;
- registry closeout must happen after merge before starting the next story.

## Target Outcome

US-AUTO-77 is complete when:

1. docs/90_codex/US_AUTO_OPERATOR_GUIDE.md exists and documents the operator workflow.
2. The guide includes the correct analyze_story_run.sh command contract.
3. The guide documents the post-merge registry closure gate.
4. The guide documents the decision model after analyze.
5. The guide documents forbidden actions.
6. analyze_story_run.sh gains additive operator-facing decision output if feasible within narrow scope.
7. Tests cover the guide-relevant analyze output and command-contract behavior if script output is changed.
8. Existing external contracts remain valid.
9. Existing targeted tests pass.

## Acceptance Criteria

- A new operator guide exists at docs/90_codex/US_AUTO_OPERATOR_GUIDE.md.
- The guide contains sections for normal path, analyze command contract, decision model after analyze, dirty tree handling, rerun required cases, rerun forbidden cases, manual-finish continuation, review/classification/gate decision path, post-merge registry closure gate, and anti-patterns.
- analyze_story_run.sh output is made clearer through additive wording only if script changes are included.
- No existing expected output wording is removed unless tests confirm the contract is intentionally preserved through equivalent or stricter output.
- The story does not implement US-AUTO-74 centralization.
- The story does not implement telemetry.
- The story does not implement stage-loop cap.
- The story does not implement test-scope optimization.
- The story does not change tests instead of fixing implementation.
- Registry remains consistent with US-AUTO-77 lifecycle.

## Validation Commands

Run targeted validation locally:

python3 -m pytest tests/test_analyze_story_run.py

If script changes touch review-stage semantics, also run:

python3 -m pytest tests/test_review_story_run.py tests/test_ai_review_story_run.py tests/test_classify_review_story_run.py tests/test_review_gate_story_run.py

Before PR, run the story pipeline according to the current automation workflow.

## Definition of Done

US-AUTO-77 is done only when:

1. Implementation is committed on feature branch.
2. Story run is completed from committed HEAD.
3. analyze is run with AUTOMATION_RUN_DIR.
4. review-stage is completed only after clean tree and HEAD/run checks.
5. review classification and review gate pass.
6. PR is merged.
7. Branch cleanup is done.
8. main is updated locally.
9. docs/90_codex/epics/US-AUTO_REGISTRY.md is checked and updated or explicitly confirmed not required.
10. US-AUTO-77 is marked Implemented in registry after merge.
11. Only then may US-AUTO-74 or another story begin.

