## Story ID and Title

US-AUTO-77 — Operator workflow simplification and decision model

## Scope Validation

Confirm:

- docs/90_codex/US_AUTO_OPERATOR_GUIDE.md was created.
- The guide includes normal workflow.
- The guide includes pre-story gate.
- The guide includes correct analyze_story_run.sh command contract.
- The guide says run dir is passed through AUTOMATION_RUN_DIR.
- The guide says run dir must not be passed as a second positional argument.
- The guide includes dirty tree handling.
- The guide includes rerun required cases.
- The guide includes rerun forbidden cases.
- The guide includes manual-finish continuation.
- The guide includes review-stage path.
- The guide includes ai_review/classify/gate path.
- The guide includes post-merge registry closure gate.
- The guide says PR merged is not story closed.
- The guide includes anti-patterns.
- The guide includes examples.

If automation/scripts/analyze_story_run.sh was modified, confirm:

- output change is additive;
- existing safety gates are preserved;
- dirty tree still blocks review-stage;
- stale run behavior is not weakened;
- committed HEAD behavior is not weakened;
- rerun-required behavior is not weakened;
- manual-finish continuation behavior is not weakened;
- script does not accept run dir as second positional argument;
- operator next action is clearer than before;
- forbidden actions are surfaced when relevant.

## Functional Validation

Confirm:

- operator guide documents the correct analyze command shape;
- operator guide documents the wrong analyze command shape as an anti-pattern;
- operator guide documents the post-merge registry closure gate;
- operator guide documents when rerun is required;
- operator guide documents when rerun is forbidden;
- operator guide documents dirty tree blocking review-stage;
- operator guide documents stale AUTOMATION_RUN_DIR invalidation after commit;
- operator guide documents manual-finish continuation safely.

Confirm no implementation changes were made to:

- semantic projection producer behavior;
- semantic projection consumer behavior;
- companion-filter centralization;
- review gate semantics;
- classifier semantics;
- telemetry;
- stage-loop cap;
- deterministic pytest selection;
- business runtime code.

## Verification

Run targeted tests:

python3 -m pytest tests/test_analyze_story_run.py

If review-stage related tests are affected, also run:

python3 -m pytest tests/test_review_story_run.py tests/test_ai_review_story_run.py tests/test_classify_review_story_run.py tests/test_review_gate_story_run.py

Before review-stage:

- git status --short is clean;
- current branch is not main;
- latest run corresponds to current HEAD;
- AUTOMATION_RUN_DIR points to the pinned run;
- analyze_story_run.sh is invoked with STORY_ID only as positional argument;
- review-stage is not run just because a next recommended command looked convenient; invariants are checked first.

After implementation PR merge:

- checkout main;
- pull latest main;
- delete local feature branch;
- delete remote feature branch if appropriate;
- check docs/90_codex/epics/US-AUTO_REGISTRY.md;
- update registry or explicitly confirm no update required;
- do not start US-AUTO-74 until closure gate is complete.

