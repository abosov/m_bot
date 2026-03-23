Story-ID: US-AUTO-41

=== FILE: 00_story.md ===
# US-AUTO-41 — Story artifacts commit handoff before run

## Objective

Ensure that every Codex run is executed on a fully committed and reproducible repository state by introducing a mandatory bundle commit boundary before run.

## Non-goals

- Do not redesign the isolated worktree execution model.
- Do not redesign review/classification/gate pipeline.
- Do not introduce post-run commits.
- Do not change artifact generation semantics beyond enforcing the pre-run commit contract.

## Dependencies

- US-AUTO-20
- US-AUTO-21
- US-AUTO-22
- US-AUTO-23
- US-AUTO-24
- US-AUTO-37
- US-AUTO-39
- runtime stabilization work already merged before this story

## Source of Truth

- automation/scripts/run_story.sh
- automation/run_codex_task.sh
- automation/scripts/check_allowed_files.sh
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md
- docs/90_codex/epics/US-AUTO_REGISTRY.md

## Current Problem

Current pipeline enforces a clean working tree before run, but it does not enforce that story bundle / prompt artifacts are already committed into repository history.

That means a run can begin from a state where:
- bundle content exists only in the working tree,
- HEAD does not yet represent the exact story contract being executed,
- reproducibility and traceability are weaker than intended.

## Core Invariant

A story run MUST begin only from a committed story-artifact state.

The system must guarantee:
- run inputs are represented by HEAD,
- review artifacts correspond to committed inputs,
- operator cannot accidentally run from an uncommitted bundle state.

## Target Outcome

Pipeline becomes:

prepare_story.sh
→ optional story-artifact commit
→ run_story.sh
→ run_codex_task.sh

with the invariant that run_codex_task.sh executes only when the relevant story artifacts are already committed.

=== FILE: 01_context_bundle.md ===
# Context Bundle

## Why this story exists

US-AUTO pipeline is now operationally stable:
- isolated worktree execution works,
- materialization back to primary checkout works,
- rollback behavior is stable,
- run artifacts are generated correctly,
- scope checks work,
- tests are green.

However, one architectural gap remains:

the pipeline still relies on the operator to ensure the story bundle / prompt state is committed before the run starts.

This is a contract gap, not a runtime bug.

## What is already good

Current runner already enforces clean-tree execution at startup via git status checks in automation/run_codex_task.sh.

That protects against arbitrary dirty working tree state, but it does not by itself guarantee that:
- the story bundle was committed,
- the run is anchored to committed bundle inputs,
- the story contract is reproducible from HEAD alone.

## Why this matters

Without an explicit pre-run commit boundary:
- the operator can prepare a bundle and forget to commit it,
- the run may be logically based on local bundle state rather than committed history,
- future enforcement stories would stack on top of a weak reproducibility contract.

## Desired architectural model

Separate responsibilities clearly:

1. prepare step
   - validates story artifact state
   - stages only story-related files when appropriate
   - creates a deterministic pre-run commit if needed

2. run step
   - execution only
   - never auto-commits
   - refuses to run if contract is violated

This keeps commit responsibility outside the runner while still automating it at workflow level.

## Preferred model

Preferred implementation is automatic prepare/commit before run, not pure fail-fast.

Reason:
- stronger operator UX,
- less manual friction,
- still deterministic,
- still keeps commit behavior explicit and isolated.

=== FILE: 02_file_scope.md ===
# File Scope

## Files Allowed To Change

- automation/scripts/run_story.sh
- automation/scripts/prepare_story.sh
- automation/scripts/commit_story_artifacts.sh
- automation/run_codex_task.sh
- tests/test_run_story.py
- tests/test_prepare_story.py
- tests/test_run_codex_task.py
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md
- docs/90_codex/epics/US-AUTO_REGISTRY.md
- tests/test_story_change_ledger.py

## Files Not Allowed To Change

- backend/**
- migrations/**
- application business logic outside automation
- review/classification/gate scripts unless strictly required by tests
- deployment scripts
- unrelated bundle packs
- automation/story_change_ledger.jsonl

## Notes

- Do not broaden scope beyond story-artifact commit contract.
- Do not redesign isolated worktree materialization.
- Do not introduce global repository staging such as git add .

=== FILE: 03_master_prompt.md ===
# Master Prompt

## Role

You are the System Architect, Workflow Engineer, and Tech Writer for Zumbot’s US-AUTO pipeline.

## Task

Implement the missing story-artifact commit handoff before run so that every story run begins from a committed and reproducible story-artifact state.

## Requirements

### 1. Introduce a dedicated prepare step

Create a new script:

automation/scripts/prepare_story.sh

Responsibilities:
- accept STORY_ID (or equivalent run context used by run_story.sh),
- determine the story artifact files that must be committed before run,
- detect whether those files are dirty relative to HEAD,
- if dirty:
  - stage only the relevant story-artifact files,
  - create a deterministic commit,
- if clean:
  - do nothing and return success.

The script must never:
- stage unrelated files,
- stage the whole repository,
- touch automation/story_change_ledger.jsonl,
- commit run artifacts.

### 2. Optional helper extraction

If useful, create:

automation/scripts/commit_story_artifacts.sh

Use it only if this improves clarity and testability.

### 3. Integrate prepare step into run workflow

Modify:

automation/scripts/run_story.sh

New high-level flow:

prepare_story.sh
→ run_codex_task.sh
→ downstream existing behavior

The prepare step must happen before runner execution.

### 4. Enforce the contract in the runner

Modify:

automation/run_codex_task.sh

Add explicit validation that the story-artifact contract is satisfied before execution continues.

Important:
- run_codex_task.sh must remain execution-only,
- it must not create commits,
- it may fail fast if story artifacts are still dirty when invoked directly or when prepare step was bypassed.

### 5. Define what counts as story artifacts

At minimum, cover the story bundle pack and any story-local prompt/bundle inputs that are intended to define the run contract.

Implementation must be grounded in the existing repository layout and current US-AUTO workflow.
Do not invent new artifact classes unless needed and justified by existing files.

### 6. Commit behavior

Use a deterministic commit message, for example:

chore(story): commit story artifacts for <STORY_ID> before run

You may refine wording slightly if repository conventions suggest a better existing pattern, but keep it explicit and deterministic.

### 7. Tests

Add focused tests that verify at least:

- dirty story artifacts trigger prepare/commit behavior,
- clean story artifacts do not create an extra commit,
- runner refuses to execute when story-artifact contract is violated,
- happy path still runs when story artifacts are already committed.

Tests must be deterministic and must not depend on remote state.

### 8. Documentation

Update:
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md
- docs/90_codex/epics/US-AUTO_REGISTRY.md

Document:
- the new prepare-before-run contract,
- that story runs are anchored to committed story-artifact state,
- that the runner itself does not commit.

## Safety Rules

- No git add .
- No git commit of unrelated working tree files.
- No weakening of clean-tree enforcement.
- No post-run commit model.
- No changes to backend/product logic outside scope.

## Architecture Intent

The final design must make this statement true:

“A story run is reproducible from committed repository history because all story-defining artifacts are committed before the run begins.”

=== FILE: 04_review_checklist.md ===
# Review Checklist

## Contract Enforcement

- [ ] Story run cannot begin from uncommitted story-artifact state.
- [ ] prepare_story.sh runs before execution.
- [ ] run_codex_task.sh does not commit.
- [ ] run_codex_task.sh fails fast if prepare step was bypassed and contract is violated.

## Scope Safety

- [ ] No repository-wide staging.
- [ ] Only story-relevant artifact files are staged.
- [ ] automation/story_change_ledger.jsonl is untouched by prepare/commit logic.
- [ ] No unrelated automation or backend files were modified.

## Determinism

- [ ] Same committed HEAD implies same story-artifact inputs for run.
- [ ] Review artifacts are generated from committed run inputs.
- [ ] No hidden operator-only preconditions remain.

## Tests

- [ ] Dirty story artifacts path covered.
- [ ] Already-clean path covered.
- [ ] Direct runner violation path covered.
- [ ] Existing happy path remains green.

## Docs

- [ ] STORY_EXECUTION_CHECKLIST updated.
- [ ] US-AUTO registry updated with the finalized contract note.

=== FILE: 05_followups.md ===
# Follow-ups

## Immediate next story after merge

- US-AUTO-25 — loop detection preflight

## Why it comes next

Once story-artifact commit boundary is enforced, loop detection and further enforcement guards can safely rely on a stronger reproducibility contract.

## Possible future improvements

- richer detection of story-local contract inputs if workflow expands,
- audit metadata linking prepare commit to subsequent run id,
- stricter validation that bundle pack and active bundle state are synchronized when applicable.

=== FILE: 06_manual_actions.md ===
# Manual Actions

## After implementation

1. Run focused tests for prepare/run behavior.
2. Run full relevant pytest suite.
3. Execute the story workflow manually from a dirty story-artifact state and verify:
   - prepare step creates the commit if needed,
   - run starts only after commit boundary is satisfied,
   - runner no longer depends on operator remembering to commit bundle artifacts.

## After merge

1. Switch to main.
2. Pull latest main.
3. Delete local and remote working branches for this story.
4. Confirm repository is clean before opening the next US-AUTO story.

## Operator verification

Expected user-visible contract:
- editing story bundle pack and immediately starting run should no longer rely on memory/manual commit discipline,
- execution must either auto-prepare the commit or fail clearly before the run begins.