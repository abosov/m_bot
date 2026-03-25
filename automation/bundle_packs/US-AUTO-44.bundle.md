# Story Bundle Pack
Story-ID: US-AUTO-44
Version: 1

=== FILE: 00_story.md ===
# US-AUTO-44 — materialization preflight & operator handoff

## Story ID and Title
- **Story ID:** US-AUTO-44
- **Title:** materialization preflight & operator handoff

## Objective
Introduce an explicit preflight contract before `automation/scripts/run_story.sh` so the workflow fails closed with deterministic operator guidance whenever the repository is not runnable because of uncommitted story-artifact state.

## Scope
In scope:
- add a dedicated preflight check for `run_story.sh`
- detect dirty working tree state with explicit handling for story artifact paths of the requested story
- print deterministic operator handoff guidance when execution is blocked
- preserve the existing clean-tree contract and fail-closed behavior
- document the canonical preflight/operator flow
- add or update automated tests

Out of scope:
- auto-comt inside `run_story.sh`
- auto-stash, auto-cleanup, or interactive prompts
- changing `run_codex_task.sh` execution ownership
- redesigning materialization behavior itself
- broad workflow refactors outside the narrow preflight/handoff contract

## Non-goals
- Do not silently modify the repository state in `run_story.sh`.
- Do not weaken existing clean-tree enforcement.
- Do not introduce implicit recovery behavior.
- Do not broaden scope into review/gate lifecycle redesign.

## Dependencies
- US-AUTO-22
- US-AUTO-23
- US-AUTO-24
- US-AUTO-38
- US-AUTO-41

## Source of Truth
- `automation/scripts/run_story.sh`
- `automation/scripts/commit_story_artifacts.sh`
- `automation/run_codex_task.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Current Code Reality
`run_story.sh` already enforces a clean git tree before execution and points to `commit_story_artifacts.sh` as the remediation helper for dirty story artifacts. However, the operator-facing contract is still too implicit and coarse: the workflow blocks, but it does not clearly formalize preflight as a named stage with deterministic handoff messaging and explicit differentiation between story-artifact dirtiness and unrelated dirtiness.

The observed friction is:
1. operator materializes or edits story artifacts
2. `run_story.sh` blocks on dirty tree
3. operator must infer what exactly must be committed or cleaned
4. reruns happen by trial and error instead of by an explicit contract

## Problem Statement
The workflow still lacks a first-class preflight/operator-handoff contract.

As a result:
- the pipeline can be perceived as failing “late” or opaquely
- the operator must infer the next action
- pressure builds to weaken the clean-tree boundary instead of making the transition explicit

## Target Outcome
The workflow becomes explicitly:

`materialize -> preflight -> operator handoff if blocked -> run`

with these guarantees:
- `run_story.sh` always performs a named dministic preflight before execution
- preflight explains whether the blocked state is caused by requested-story artifacts or unrelated dirty paths
- operator guidance is explicit, actionable, and stable
- clean-tree enforcement remains fail-closed
- the pipeline never starts from a state that is not execution-safe

## Functional Requirements
1. `run_story.sh` must execute an explicit preflight stage before validation and execution.
2. The preflight stage must inspect the current git dirty state excluding approved ephemeral ledger behavior.
3. If the tree is clean, the story may continue normally.
4. If dirty paths belong only to the requested story artifact paths, `run_story.sh` must fail closed with a deterministic handoff message that points to:
   - review the changes
   - run `automation/scripts/commit_story_artifacts.sh <STORY_ID>`
   - rerun `automation/scripts/run_story.sh <STORY_ID>`
5. If dirty paths include unrelated repository changes, `run_story.sh` must fail closed with a deterministic cleanup/remediation message and must not suggest committing unrelated paths through the story handoff flow.
6. The operator-facing message must clearly distinguish:
   - requested story artifact dirtiness
   - unrelated dirty repository state
7. Documentation must describe preflight as an explicit stage in the canonical operator flow.
8. Tests must cover clean, story-artifact-dirty, and unrelated-dirty scenarios.

## Acceptance Criteria
- `run_story.sh` has an explicit preflight stage.
- Clean repositories pass preflight and continue.
- Dirty requested-story artifacts produce a deterministic operator handoff message.
- Unrelated dirty paths produce a deterministic blocked message without broadening commit scope.
- No auto-commit or auto-cleanup is introduced.
- Relevant tests pass.
- Docs and registry match the contract.

## Risks
- path classification may accidentally blur story-artifact dirtiness and unrelated dirtiness
- error messaging may drift from real behavior if not tested
- preflight changes may unintentionally weaken existing guardrails if implemented too broadly

## Done Definition
Story is done only when implementation, tests, documentation, and registry updates all reflect an explicit fail-closed preflight/operator-handoff contract for `run_story.sh`.

=== FILE: 01_context_bundle.md ===
# Context Bundle — US-AUTO-44

## Source of Truth
- `automation/scripts/run_story.sh`
- `automation/scripts/commit_story_artifacts.sh`
- `automation/run_codex_task.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Current Code Reality
`automation/scripts/run_story.sh` already enforces a clean working tree before execution and fails closed when the repository is dirty. It also points the operator toward `automation/scripts/commit_story_artifacts.sh` when story artifacts must be committed before execution.

However, the current contract is still too implicit:
- preflight is not expressed as a first-class named workflow stage
- the blocked condition is not clearly classified for the operator
- requested-story artifact dirtiness and unrelated repository dirtiness are not surfaced as separate operator-facing cases
- the operator must infer the correct next action from a generic dirty-tree failure

As a result, the workflow is safe but still operationally noisy.

## Architectural Context
The US-AUTO automation pipeline already has clear ownership boundaries:
- `run_story.sh` owns orchestration and execution gating
- `commit_story_artifacts.sh` owns explicit operator handoff for committing story artifacts
- `run_codex_task.sh` owns isolated execution and materialization mechanics
- docs and registry own workflow contract visibility

This story must preserve those boundaries.
It must not move commit ownership into `run_story.sh`.
It must not redesign materialization.
It must only make the preflight/operator-handoff stage explicit and deterministic.

## Architectural Intent
The desired workflow contract is:

`materialize -> preflight -> operator handoff if blocked -> run`

Architecturally, that means:
- `run_story.sh` performs an explicit preflight stage before execution
- preflight classifies the dirty state narrowly for the requested story
- if only requested-story artifact paths are dirty, the script gives a deterministic handoff to `commit_story_artifacts.sh`
- if unrelated paths are dirty, the script blocks with a different deterministic remediation message
- execution starts only from a repository state that is explicitly safe

This preserves fail-closed governance while improving operator clarity.

## Constraints
- fail closed
- no auto-commit
- no auto-stash
- no auto-cleanup
- no materialization redesign
- no scope expansion into review/gate lifecycle changes
- keep messages deterministic and regression-testable

## Risks
- path classification may accidentally misclassify unrelated dirty paths as story-artifact dirtiness
- messaging may diverge from actual script behavior if not covered by tests
- preflight refactoring may unintentionally weaken the existing clean-tree contract if implemented too broadly
- documentation may drift if the operator flow wording is updated in code but not in docs

## Acceptance Notes
Successful implementation should result in the following observable behavior:

1. clean repository:
- `run_story.sh <STORY_ID>` passes preflight and continues normally

2. dirty requested-story artifacts only:
- `run_story.sh <STORY_ID>` fails closed
- output clearly says preflight failed because requested story artifacts are uncommitted
- output tells the operator to:
  - review changes
  - run `automation/scripts/commit_story_artifacts.sh <STORY_ID>`
  - rerun `automation/scripts/run_story.sh <STORY_ID>`

3. unrelated dirty repository state:
- `run_story.sh <STORY_ID>` fails closed
- output clearly says unrelated dirty repository state is present
- output does not suggest broad story-artifact commit handoff for unrelated changes

4. workflow contract:
- docs describe preflight as an explicit stage
- registry reflects US-AUTO-44 as the explicit preflight/operator-handoff story

=== FILE: 02_file_scope.md ===
# File Scope — US-AUTO-44

## Files Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/bundle_packs/US-AUTO-44.bundle.md`
- `automation/bundles/active/US-AUTO-44/00_story.md`
- `automation/bundles/active/US-AUTO-44/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-44/02_file_scope.md`
- `automation/bundles/active/US-AUTO-44/03_master_prompt.md`
- `automation/bundles/active/US-AUTO-44/04_review_checklist.md`
- `automation/bundles/active/US-AUTO-44/05_followups.md`
- `automation/bundles/active/US-AUTO-44/06_manual_actions.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `tests/test_run_story.py`
- `tests/test_story_change_ledger.py`

## Files Not Allowed To Change
- `automation/scripts/commit_story_artifacts.sh`
- `automation/run_codex_task.sh`
- review/classification/gate scripts
- rollback lifecycle logic
- unrelated workflow scripts
- application runtime code outside automation workflow docs/tests

## Rationale
This story is about explicit preflight classification and operator messaging in `run_story.sh`, not about changing artifact commit ownership or execution behavior. `commit_story_artifacts.sh` is already the explicit commit handoff boundary and must remain unchanged unless a later story explicitly targets it.

Because scope validation compares the full branch diff against `origin/main`, the canonical story bundle artifacts for US-AUTO-44 and the narrow run-story test file must be explicitly allowlisted for this story.

## Expected Test Surface
Use `tests/test_run_story.py` for narrowly scoped regression coverage around:
- clean tree passes preflight
- requested-story artifact dirtiness prints handoff message
- unrelated dirtiness prints cleanup/remediation message

## Path Rules
- No new broad utility modules.
- No cross-cutting refactor.
- Keep edits local to the workflow contract.

=== FILE: 03_master_prompt.md ===
# Master Prompt — US-AUTO-44

## Role
You are a senior workflow engineer, shell-script implementer, test author, and technical writer working inside the Zumbot US-AUTO automation contract.

## Goal
Implement **US-AUTO-44 — materialization preflight & operator handoff** as a narrow workflow-contract story. Make preflight in `run_story.sh` explicit, deterministic, and operator-readable without weakening existing clean-tree enforcement.

## Source of Truth
- `automation/scripts/run_story.sh`
- `automation/scripts/commit_story_artifacts.sh`
- `automation/run_codex_task.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Files Allowed To Change
- `automation/scripts/run_story.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- only the minimum test files required for this story

## Files Not Allowed To Change
- `automation/scripts/commit_story_artifacts.sh`
- `automation/run_codex_task.sh`
- review/classification/gate scripts
- rollback lifecycle logic
- unrelated workflow scripts
- application runtime code outside automation workflow docs/tests

## Requirements
1. Add an explicit preflight stage to `automation/scripts/run_story.sh`.
2. Preflight must classify dirty paths for the requested story using narrow allowlist logic.
3. If only requested-story artifact paths are dirty, print a deterministic operator handoff message that instructs the operator to:
   - review changes
   - run `automation/scripts/commit_story_artifacts.sh <STORY_ID>`
   - rerun `automation/scripts/run_story.sh <STORY_ID>`
4. If unrelated dirty paths exist, print a deterministic blocked message instructing the operator to resolve those changes outside the story-artifact handoff flow.
5. Keep clean-tree enforcement fail-closed.
6. Do not introduce auto-commit, auto-stash, or auto-cleanup behavior.
7. Update documentation and epic registry to describe preflight as a first-class workflow stage.
8. Add or update tests for clean, story-artifact-dirty, and unrelated-dirty scenarios.

## Constraints
- do not weaken clean-tree enforcement
- do not modify `commit_story_artifacts.sh`
- do not move commit ownership into `run_story.sh`
- do not broaden scope into materialization redesign
- use deterministic, testable messages
- keep the patch minimal and local

## Output
Deliver:
- minimal `run_story.sh` preflight implementation
- narrow tests
- doc updates
- registry update

Before finishing:
- run relevant tests
- verify docs match behavior
- confirm no unrelated files changed

## Atomic Task Isolation
Implement exactly one workflow contract improvement:
**explicit preflight classification and operator handoff in `run_story.sh`.**

Do not use this story to fix adjacent workflow friction.
If you discover follow-up opportunities, record them in follow-ups instead of extending scope.

## Definition of Success
The workflow must clearly tell the operator:
- why execution is blocked
- whether the block is due to requested-story artifacts or unrelated changes
- exactly what to do next

=== FILE: 04_review_checklist.md ===
# Review Checklist — US-AUTO-44

## Scope Validation
- [ ] only allowed files changed
- [ ] no unrelated refactors introduced
- [ ] `commit_story_artifacts.sh` was not modified
- [ ] `run_codex_task.sh` was not modified
- [ ] rollback behavior was not broadened or weakened

## Functional Validation
- [ ] `run_story.sh` contains an explicit preflight stage
- [ ] clean tree continues normally
- [ ] request-story artifact dirtiness produces deterministic handoff output
- [ ] unrelated dirty paths produce deterministic blocked output
- [ ] operator guidance includes exact next commands
- [ ] no auto-commit exists in run flow
- [ ] no auto-clean exists in run flow
- [ ] clean-tree enforcement remains fail-closed

## Verification
- [ ] relevant tests pass
- [ ] docs updated
- [ ] epic registry updated
- [ ] canonical operator flow documents preflight explicitly

## Messaging Validation
- [ ] blocked messages clearly distinguish story-artifact dirtiness from unrelated dirtiness
- [ ] messages are stable enough for regression tests
- [ ] remediation does not suggest broad commits outside the story scope

=== FILE: 05_followups.md ===
# US-AUTO-44: Follow-Ups

## Follow-Up Prompt Queue
- Add a lightweight helper that previews classified dirty paths before the operator chooses a remediation action.
- Add a status command that prints workflow stage plus preflight classification without attempting execution.
- Consider a later story for richer operator UX around materialization readiness.
- Consider a later story for tighter integration between analyze output and preflight diagnostics.
- Revisit whether `commit_story_artifacts.sh` and `run_story.sh` should share a common read-only path-classification helper in a separate contract-focused story.

## Iteration Notes
- Keep US-AUTO-44 narrow and message-contract focused.
- Do not convert preflight into mutation.
- Do not redesign materialization.
- Prefer stable output over clever behavior.

## Deferred Questions
- Should preflight output become machine-readable in a later story?
- Should analyze consume the same preflight classification helper in a later story?
- Should there be a dedicated `check_story_ready.sh` helper, or is that unnecessary duplication?

=== FILE: 06_manual_actions.md ===
# US-AUTO-44: Manual Actions

## Required Human Actions
- Rebuild the bundle pack after any bundle edits.
- Materialize the active bundle before execution when needed.
- If preflight reports requested-story artifact dirtiness:
  - review changes
  - run `automation/scripts/commit_story_artifacts.sh <STORY_ID>`
  - rerun `automation/scripts/run_story.sh <STORY_ID>`
- If preflight reports unrelated dirty paths:
  - resolve those changes outside the story-artifact handoff flow
  - rerun `automation/scripts/run_story.sh <STORY_ID>`
- Continue review → classify → review_gate after a successful run.

## Completion Status

### Current State
- Bundle prepared.
- Story defined as narrow preflight/operator-handoff contract work.
- Awaiting materialization, implementation, and review.

### Expected Operator Flow
1. `automation/scripts/materialize_story_bundle.sh US-AUTO-44`
2. `automation/scripts/run_story.sh US-AUTO-44`
3. if blocked by requested-story artifacts:
   - `automation/scripts/commit_story_artifacts.sh US-AUTO-44`
   - `automation/scripts/run_story.sh US-AUTO-44`
4. if blocked by unrelated dirtths:
   - resolve them outside the handoff flow
   - `automation/scripts/run_story.sh US-AUTO-44`
5. review → classify → review_gate
6. open PR and finalize via standard US-AUTO flow

### Registry Expectation
Update `docs/90_codex/epics/US-AUTO_REGISTRY.md` so US-AUTO-44 is visible as the explicit preflight/operator-handoff story following the commit-handoff work introduced earlier.
