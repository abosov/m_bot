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

