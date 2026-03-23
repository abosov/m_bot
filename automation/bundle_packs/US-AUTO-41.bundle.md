Story-ID: US-AUTO-41

=== FILE: 00_story.md ===
# US-AUTO-41 — Story artifacts commit handoff before run

## Objective

Ensure that every story run starts from a fully committed and reproducible story-artifact state by enforcing an explicit commit handoff before `run_story.sh`.

## Non-goals

- Do not redesign the isolated worktree execution model.
- Do not redesign review/classification/gate pipeline.
- Do not introduce post-run commits.
- Do not move commit ownership into `run_codex_task.sh`.
- Do not change artifact generation semantics beyond enforcing the pre-run committed-artifact contract.

## Dependencies

- US-AUTO-20
- US-AUTO-21
- US-AUTO-22
- US-AUTO-23
- US-AUTO-24
- US-AUTO-37
- US-AUTO-38
- runtime stabilization work already merged before this story

## Source of Truth

- automation/scripts/run_story.sh
- automation/scripts/commit_story_artifacts.sh
- automation/run_codex_task.sh
- automation/scripts/check_allowed_files.sh
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md
- docs/90_codex/epics/US-AUTO_REGISTRY.md

## Current Problem

Current pipeline enforces a clean working tree before run, but it did not enforce that story bundle / prompt artifacts were already committed into repository history before `run_story.sh` delegated to the runner.

That meant a run could begin from a state where:
- bundle content existed only in the working tree,
- HEAD did not yet represent the exact story contract being executed,
- reproducibility and traceability were weaker than intended.

## Core Invariant

A story run MUST begin only from a committed story-artifact state.

The system must guarantee:
- run inputs are represented by HEAD,
- review artifacts correspond to committed inputs,
- operator cannot accidentally run from an uncommitted story-artifact state.

## Target Outcome

Pipeline becomes:

commit_story_artifacts.sh
→ run_story.sh
→ run_codex_task.sh

with the invariant that:
- `commit_story_artifacts.sh` is the canonical pre-run handoff helper,
- `run_story.sh` blocks execution until story artifacts are committed,
- `run_codex_task.sh` remains execution-only.

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

However, one architectural gap remained:

the pipeline still relied on the operator to ensure the story bundle / prompt state was committed before the run started.

This was a contract gap, not a runtime bug.

## What is already good

Current runner already enforces clean-tree execution at startup via git status checks in `automation/run_codex_task.sh`.

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

1. commit handoff helper
   - validates story artifact state,
   - stages only story-related files when appropriate,
   - creates a deterministic pre-run commit when needed.

2. run step
   - execution only,
   - never auto-commits,
   - refuses to run if contract is violated.

This keeps commit responsibility outside the runner while making the remediation path explicit and deterministic.

## Implemented model

The implemented model is explicit helper + fail-fast guard, not auto-prepare inside the runner:

- `automation/scripts/commit_story_artifacts.sh`
  - canonical helper for story-artifact commit handoff
- `automation/scripts/run_story.sh`
  - blocks if required story artifacts are still dirty
  - points the operator to the helper
- `automation/run_codex_task.sh`
  - remains execution-only
  - does not create commits

This is the shipped contract and the canonical pack must match it exactly.

=== FILE: 02_file_scope.md ===
# File Scope

## Files Allowed To Change

- automation/scripts/run_story.sh
- automation/scripts/commit_story_artifacts.sh
- automation/run_codex_task.sh
- tests/test_run_story.py
- tests/test_story_bundle_scripts.py
- tests/test_story_change_ledger.py
- docs/90_codex/STORY_BUNDLE_SPEC.md
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md
- docs/90_codex/epics/US-AUTO_REGISTRY.md

## Files Not Allowed To Change

- backend/**
- migrations/**
- application business logic outside automation
- review/classification/gate scripts unless strictly required by tests
- deployment scripts
- unrelated tests outside the explicit allowed file list
- unrelated bundle packs
- automation/story_change_ledger.jsonl

## Notes

- Do not broaden scope beyond the story-artifact commit contract.
- Do not redesign isolated worktree materialization.
- Do not introduce global repository staging such as `git add .`.
- If additional files become necessary, update both active bundle scope and canonical bundle pack scope together.

=== FILE: 03_master_prompt.md ===
# Master Prompt — US-AUTO-41

## Role
You are a senior workflow engineer, shell-script implementer, test author, and technical writer working inside the Zumbot US-AUTO automation contract.

## Goal
Implement **US-AUTO-41 — Story artifacts commit handoff before run** as a narrow workflow-contract story. Add a canonical explicit commit handoff step between materialization and execution without weakening the clean-tree boundary.

## Source of Truth
- `automation/scripts/new_story_bundle.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/run_story.sh`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Files Allowed To Change
- `automation/scripts/commit_story_artifacts.sh`
- `automation/scripts/run_story.sh`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/run_codex_task.sh`
- only the minimum test files required for this story

## Files Not Allowed To Change
- unrelated workflow scripts
- application runtime code unrelated to story execution workflow
- rollback contract logic except where explicitly necessary for compatibility

## Requirements
1. Add `automation/scripts/commit_story_artifacts.sh <STORY_ID>`.
2. The script must only stage and commit:
   - `automation/bundle_packs/<STORY_ID>.bundle.md`
   - `automation/bundles/active/<STORY_ID>/**`
3. The script must fail on unrelated dirty paths anywhere else in the repo.
4. The script must fail when no eligible changes exist.
5. The script must use a deterministic commit message.
6. `run_story.sh` must block on dirty story artifacts and print a deterministic remediation hint.
7. Update docs and registry.
8. Add or update tests.

## Constraints
- do not weaken clean-tree enforcement
- do not implement implicit auto-commit inside `run_story.sh`
- do not opportunistically refactor unrelated code
- use allowlist path matching, not broad exclusions

## Output
Deliver:
- implementation of the new handoff script
- minimal update to `run_story.sh`
- tests
- doc updates
- epic registry update

Before finishing:
- run relevant tests
- verify docs match behavior
- confirm no unrelated files changed

=== FILE: 04_review_checklist.md ===
# Review Checklist

## Contract Enforcement

- [ ] Story run cannot begin from uncommitted story-artifact state.
- [ ] `commit_story_artifacts.sh` is the canonical pre-run handoff helper.
- [ ] `run_story.sh` blocks execution until the contract is satisfied.
- [ ] `run_codex_task.sh` does not commit and does not own the handoff contract.

## Scope Safety

- [ ] No repository-wide staging.
- [ ] Only story-relevant artifact files are staged.
- [ ] `automation/story_change_ledger.jsonl` is untouched by commit-handoff logic.
- [ ] No unrelated automation, backend, or out-of-scope test files were modified.

## Determinism

- [ ] Same committed HEAD implies the same story-artifact inputs for run.
- [ ] Review artifacts are generated from committed run inputs.
- [ ] No hidden operator-only preconditions remain.

## Tests

- [ ] Dirty story-artifact blocking path covered.
- [ ] Already-clean path covered.
- [ ] Unrelated dirty-path blocking path covered.
- [ ] Existing happy path remains green.

## Docs

- [ ] Canonical bundle pack matches the implemented contract.
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
- audit metadata linking handoff commit to subsequent run id,
- stricter validation that bundle pack and active bundle state are synchronized when applicable.

=== FILE: 06_manual_actions.md ===
# Manual Actions

## After implementation

1. Run focused tests for handoff/run behavior.
2. Run full relevant pytest suite.
3. Execute the story workflow manually from a dirty story-artifact state and verify:
   - `run_story.sh` blocks clearly,
   - `automation/scripts/commit_story_artifacts.sh <STORY_ID>` creates the expected commit when appropriate,
   - `run_codex_task.sh` remains execution-only,
   - runner no longer depends on operator memory about uncommitted bundle artifacts.

## After merge

1. Switch to main.
2. Pull latest main.
3. Delete local and remote working branches for this story.
4. Confirm repository is clean before opening the next US-AUTO story.

## Operator verification

Expected user-visible contract:
- editing story bundle pack or active story artifacts and immediately starting run should no longer rely on memory/manual discipline alone,
- `run_story.sh` must fail clearly until committed story-artifact state is restored,
- `automation/scripts/commit_story_artifacts.sh <STORY_ID>` is the canonical remediation path before rerunning.