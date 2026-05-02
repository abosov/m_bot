Story-ID: US-AUTO-77
Title: Operator workflow simplification and decision model
Status: Draft bundle
Priority: P1
Type: follow-up
Source-Of-Truth: docs/90_codex/epics/US-AUTO_REGISTRY.md

=== FILE: 00_story.md ===
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

=== FILE: 01_context_bundle.md ===
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

=== FILE: 02_file_scope.md ===
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

=== FILE: 03_master_prompt.md ===
## Story ID and Title

US-AUTO-77 — Operator workflow simplification and decision model

## Role

You are working as architect, developer, QA, and technical writer for the Zumbot US-AUTO automation pipeline.

## Goal

Implement US-AUTO-77 with a narrow, safety-preserving scope.

Reduce operator cognitive load after run/analyze without weakening committed-HEAD, pinned-run, rerun, review-stage, classification, gate, or registry closeout invariants.

The story must create a practical operator guide and, if feasible within scope, improve analyze_story_run.sh output with an additive operator decision section.

## Source of Truth

Use these files as source of truth:

- docs/90_codex/epics/US-AUTO_REGISTRY.md
- automation/bundle_packs/US-AUTO-77.bundle.md
- automation/bundles/active/US-AUTO-77/00_story.md
- automation/bundles/active/US-AUTO-77/01_context_bundle.md
- automation/bundles/active/US-AUTO-77/02_file_scope.md
- automation/bundles/active/US-AUTO-77/04_review_checklist.md

Respect existing behavior in:

- automation/scripts/analyze_story_run.sh
- tests/test_analyze_story_run.py

## Files Allowed To Change

docs/90_codex/US_AUTO_OPERATOR_GUIDE.md

automation/scripts/analyze_story_run.sh

tests/test_analyze_story_run.py

docs/90_codex/README.md

docs/90_codex/epics/US-AUTO_REGISTRY.md

## Files Not Allowed To Change

automation/scripts/run_story.sh

automation/scripts/review_story_run.sh

automation/scripts/ai_review_story_run.sh

automation/scripts/classify_review_story_run.sh

automation/scripts/review_gate_story_run.sh

automation/scripts/next_step.sh

Do not change semantic projection producer or consumer internals.

Do not change companion-filter centralization.

Do not change review-fidelity helper internals.

Do not change stage-loop cap logic.

Do not add telemetry.

Do not add deterministic pytest selection.

Do not change business runtime code.

Do not change OAuth scopes.

Do not add database migrations.

## Required Work

Create:

docs/90_codex/US_AUTO_OPERATOR_GUIDE.md

The guide must include these sections:

- Normal workflow
- Pre-story gate
- run_story stage
- analyze stage
- Correct analyze_story_run.sh command contract
- Operator decision model after analyze
- Dirty tree handling
- Rerun required cases
- Rerun forbidden cases
- Manual-finish continuation
- Review-stage path
- AI review, classification, and review gate path
- Post-merge registry closure gate
- Anti-patterns
- Examples

The guide must explicitly state that analyze_story_run.sh receives the run directory through AUTOMATION_RUN_DIR.

Correct:

AUTOMATION_RUN_DIR=automation/runs/<STORY_ID>/<RUN_DIR> automation/scripts/analyze_story_run.sh <STORY_ID>

Incorrect:

automation/scripts/analyze_story_run.sh <STORY_ID> automation/runs/<STORY_ID>/<RUN_DIR>

The guide must explicitly state:

PR merged is not story closed.

Story closed requires:

1. PR merged.
2. Branch cleanup done.
3. main updated locally.
4. registry checked.
5. registry updated or explicitly confirmed not required.

Optionally modify:

automation/scripts/analyze_story_run.sh

Only if this can be done additively and safely.

Add a clear operator-facing decision section such as:

OPERATOR DECISION:
- Current state:
- Required next action:
- Allowed actions:
- Forbidden actions:
- Why:

This section must not weaken existing decisions.

It must not make review-stage allowed when existing logic blocks it.

It must not make rerun optional when existing logic requires it.

It must not hide dirty tree blockers.

It must not accept the run directory as a second positional argument.

Modify:

tests/test_analyze_story_run.py

Add or update tests that verify:

- analyze output includes the operator decision section when appropriate;
- analyze output documents or preserves the correct AUTOMATION_RUN_DIR command shape;
- conflicting or mixed signals are clarified by a single next-action decision if fixture coverage exists;
- dirty tree still blocks review-stage;
- manual-finish continuation guidance remains safe if fixture coverage exists.

Do not remove existing assertions unless the existing wording is replaced by stricter compatible wording.

## Output

Return:

- concise summary of changed files;
- tests run;
- any follow-up recommendations;
- whether next_step.sh should remain a follow-up;
- confirmation that no semantic projection or review gate behavior was changed.

Do not claim the story is closed.

Story closure happens only after PR merge, cleanup, main update, and registry closeout.

=== FILE: 04_review_checklist.md ===
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

=== FILE: 05_followups.md ===
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

=== FILE: 06_manual_actions.md ===
## Story ID and Title

US-AUTO-77 — Operator workflow simplification and decision model

## Required Human Actions

Before materialize, run locally from the repository root:

git status --short && git branch --show-current

Expected:

- branch is feat/us-auto-77-operator-workflow-simplification;
- working tree is clean except the newly created or modified bundle pack before commit.

Materialize:

automation/scripts/materialize_story_bundle.sh US-AUTO-77

Validate:

automation/scripts/validate_story_bundle.sh US-AUTO-77

Inspect generated files:

find automation/bundles/active/US-AUTO-77 -maxdepth 1 -type f -print

Open files in Cursor:

open -a "Cursor" automation/bundle_packs/US-AUTO-77.bundle.md
open -a "Cursor" automation/bundles/active/US-AUTO-77/00_story.md
open -a "Cursor" automation/bundles/active/US-AUTO-77/03_master_prompt.md

Commit bundle artifacts:

git status --short
git add automation/bundle_packs/US-AUTO-77.bundle.md automation/bundles/active/US-AUTO-77
git commit -m "docs(us-auto): add US-AUTO-77 story bundle"

Run story locally on the feature branch, not on main.

After run completes, do not jump directly to review-stage.

First analyze.

Use only STORY_ID as positional argument.

Correct analyze shape:

AUTOMATION_RUN_DIR=automation/runs/US-AUTO-77/<RUN_DIR> automation/scripts/analyze_story_run.sh US-AUTO-77

Wrong analyze shape:

automation/scripts/analyze_story_run.sh US-AUTO-77 automation/runs/US-AUTO-77/<RUN_DIR>

Before review-stage, check:

git status --short

If dirty tree exists, resolve it first.

If only automation/story_change_ledger.jsonl is dirty and it is unintended ledger-only dirtiness, run:

git restore automation/story_change_ledger.jsonl

Run targeted tests locally:

python3 -m pytest tests/test_analyze_story_run.py

If review-stage semantics are touched, also run:

python3 -m pytest tests/test_review_story_run.py tests/test_ai_review_story_run.py tests/test_classify_review_story_run.py tests/test_review_gate_story_run.py

After implementation and tests pass:

git status --short

Then add only intended files and commit:

git add docs/90_codex/US_AUTO_OPERATOR_GUIDE.md automation/scripts/analyze_story_run.sh tests/test_analyze_story_run.py docs/90_codex/README.md docs/90_codex/epics/US-AUTO_REGISTRY.md
git commit -m "US-AUTO-77: Add operator workflow decision model"

If some optional files were not changed, omit them from git add.

After any new commit, previous AUTOMATION_RUN_DIR is invalid.

Run the story again or follow the explicit manual-finish continuation contract if analyze says that is the valid path.

Do not reuse a stale run for review-stage.

Before review-stage:

git status --short
git rev-parse HEAD

Then analyze the pinned committed-head run:

AUTOMATION_RUN_DIR=automation/runs/US-AUTO-77/<RUN_DIR> automation/scripts/analyze_story_run.sh US-AUTO-77

Only continue if analyze says review-stage is allowed and tree is clean.

Push current branch:

git pushup

Create PR with gh according to project workflow.

Do not mark story closed after PR creation.

Do not mark story closed immediately after merge.

After implementation PR is merged, run locally:

git checkout main && git pull --ff-only origin main

Clean branches according to project workflow.

Then check registry:

open -a "Cursor" docs/90_codex/epics/US-AUTO_REGISTRY.md

Update US-AUTO-77 only after merge:

- Status: Implemented;
- PR number;
- pinned run;
- note that operator guide and decision model were added.

Commit registry closeout in a separate branch/PR if current workflow requires it.

Only after registry closeout is merged or explicitly confirmed not required may US-AUTO-74 begin.

## Completion Status

Not complete at bundle creation time.

Completion requires:

1. bundle materialized;
2. bundle validated;
3. bundle artifacts committed;
4. implementation completed;
5. targeted tests passed;
6. story run completed;
7. analyze completed with AUTOMATION_RUN_DIR;
8. review-stage completed only with clean tree and valid pinned run;
9. classification and gate passed;
10. implementation PR merged;
11. branch cleanup completed;
12. main updated locally;
13. registry closeout checked and completed.

