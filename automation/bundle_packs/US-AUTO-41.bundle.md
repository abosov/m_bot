Story-ID: US-AUTO-41
Title: Story artifacts commit handoff before run
Epic: US-AUTO
Status: Draft
Owner: Codex workflow
Bundle-Type: story
Bundle-Format-Version: 1

=== FILE: 00_story.md ===
# US-AUTO-41 — Story artifacts commit handoff before run

## Story ID and Title
- **Story ID:** US-AUTO-41
- **Title:** Story artifacts commit handoff before run

## Objective
Introduce a canonical explicit handoff step between story bundle materialization and story execution so that generated story artifacts are committed before `run_story.sh` begins.

## Scope
In scope:
- add a dedicated script to commit story artifacts for a single story
- preserve the existing clean-tree contract in `automation/scripts/run_story.sh`
- make `run_story.sh` fail with a deterministic remediation hint when requested story artifacts are dirty
- document the canonical sequence `materialize -> commit -> run`
- add or update automated tests

Out of scope:
- auto-commit inside `run_story.sh`
- weakening clean-tree enforcement
- batching multiple stories in one commit flow
- redesigning bundle generation
- changing rollback lifecycle introduced by US-AUTO-38

## Non-goals
- Do not make `run_story.sh` silently commit files.
- Do not broaden allowed commit scope beyond story artifacts for the requested story.
- Do not fix unrelated workflow pain points in the same story.

## Dependencies
- US-AUTO-22
- US-AUTO-23
- US-AUTO-24
- US-AUTO-38

## Source of Truth
- `automation/scripts/new_story_bundle.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/run_story.sh`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Current Code Reality
After `new_story_bundle.sh` and `materialize_story_bundle.sh`, the repository contains newly created or modified story artifacts:
- `automation/bundle_packs/<STORY_ID>.bundle.md`
- `automation/bundles/active/<STORY_ID>/**`

`automation/scripts/run_story.sh` correctly enforces a clean git tree before execution. Because generated story artifacts are uncommitted at that point, the operator must manually inspect, add, and commit them before every run.

## Problem Statement
The workflow has no canonical transition from:
`materialize -> committed -> runnable`

This causes repeated manual friction and invites pressure to weaken the clean-tree contract instead of formalizing the missing handoff.

## Target Outcome
The workflow becomes:
`new_story_bundle -> materialize -> commit_story_artifacts -> run_story`

with these guarantees:
- `run_story.sh` never executes against uncommitted story artifacts
- only story artifact paths for the requested story can be committed by the handoff step
- the handoff step fails when unrelated repository changes exist
- the operator gets a deterministic next action when execution is blocked

## Functional Requirements
1. Add a dedicated explicit script for committing story artifacts for one story id.
2. The script must accept `<STORY_ID>` as its argument.
3. The script must only stage and commit:
   - `automation/bundle_packs/<STORY_ID>.bundle.md`
   - `automation/bundles/active/<STORY_ID>/**`
4. The script must fail if there are unrelated modified, deleted, untracked, or staged changes outside those allowed paths.
5. The script must fail if no eligible changes exist for the requested story.
6. The script must use a deterministic commit message.
7. `run_story.sh` must detect dirty story artifacts for the requested story and block with a remediation hint.
8. Documentation must describe the new canonical handoff step.

## Acceptance Criteria
- A dedicated handoff script exists and is documented.
- The handoff script commits only allowed artifact paths for the requested story.
- The handoff script fails on unrelated changes.
- The handoff script fails when there is nothing to commit.
- `run_story.sh` blocks on dirty story artifacts and points to the handoff script.
- Tests cover success and failure paths.
- Docs and epic registry are updated to match the workflow contract.

## Risks
- path matching may be too broad and accidentally include unrelated files
- commit behavior may leak into run behavior
- partial or surprising commits may weaken operator trust

## Done Definition
Story is done only when implementation, tests, documentation, and registry updates all reflect the canonical explicit handoff:
`materialize -> commit -> run`

=== FILE: 01_context_bundle.md ===
# Context Bundle — US-AUTO-41

## Why This Story Exists
US-AUTO-38 fixed rollback and cleanup behavior after failed or interrupted runs. That reduced dirty-tree problems after execution, but it did not address the operator friction before execution. Bundle creation and materialization still generate files that must be committed manually before `run_story.sh` can pass its clean-tree preflight.

## Source of Truth
- `automation/scripts/new_story_bundle.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/run_story.sh`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Current Code Reality
The current operator flow is effectively:
1. create bundle
2. materialize bundle
3. hit clean-tree block in `run_story.sh`
4. manually inspect and commit generated story files
5. rerun

This is not a correctness bug in `run_story.sh`; it is a missing explicit workflow state transition.

## Architectural Intent
Formalize a distinct transition state between materialization and execution:
- **draft**: story artifacts exist but are uncommitted
- **committed**: story artifacts are committed and the tree is clean
- **runnable**: `run_story.sh` may proceed

The design intent is to preserve strict clean-tree enforcement while removing guesswork around what must be committed.

## UX Intent
The operator should no longer have to infer the next step. When story artifacts are dirty, the system should point to one explicit command that performs the narrow, contract-backed commit handoff.

Desired operator flow:
1. create bundle
2. materialize
3. `automation/scripts/commit_story_artifacts.sh <STORY_ID>`
4. `automation/scripts/run_story.sh <STORY_ID>`

## Risks
- broad matching logic may accidentally include unrelated files
- hidden auto-commit behavior would blur responsibility boundaries
- too much scope in this story could turn a narrow contract fix into another workflow redesign

## Acceptance Notes
Keep this story narrow. The goal is to make the missing handoff canonical, not to introduce automation layers beyond that handoff.

=== FILE: 02_file_scope.md ===
# File Scope — US-AUTO-41

## Files Allowed To Change
- `automation/bundle_packs/US-AUTO-41.bundle.md`
- `automation/bundles/active/US-AUTO-41/00_story.md`
- `automation/bundles/active/US-AUTO-41/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-41/02_file_scope.md`
- `automation/bundles/active/US-AUTO-41/03_master_prompt.md`
- `automation/bundles/active/US-AUTO-41/04_review_checklist.md`
- `automation/bundles/active/US-AUTO-41/05_followups.md`
- `automation/bundles/active/US-AUTO-41/06_manual_actions.md`
- `automation/scripts/commit_story_artifacts.sh`
- `automation/scripts/run_story.sh`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `tests/test_run_story.py`
- `tests/test_story_bundle_scripts.py`
- `automation/run_codex_task.sh`

## Files Not Allowed To Change
- rollback lifecycle implementation introduced by US-AUTO-38, except where strictly necessary for compatibility within `automation/scripts/run_story.sh`
- bundle generation semantics outside the US-AUTO-41 bundle artifacts listed above
- unrelated workflow scripts
- application code outside automation/docs/tests scope
- any tests other than:
  - `tests/test_run_story.py`
  - `tests/test_story_bundle_scripts.py`

## Implementation Notes
The new handoff script must allowlist only these artifact paths for `<STORY_ID>`:
- `automation/bundle_packs/<STORY_ID>.bundle.md`
- `automation/bundles/active/<STORY_ID>/**`

For this story, the bundle artifacts themselves are also part of the allowed changed-file scope because they are versioned and committed as part of the story branch before execution.

`run_story.sh` must remain strict and must not auto-commit. It may only improve targeted preflight messaging for dirty story artifacts.

## Test Notes
Cover at minimum:
- artifact-only commit succeeds
- unrelated changes cause failure
- nothing-to-commit causes failure
- `run_story.sh` blocks on dirty story artifacts and prints remediation

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
# Review Checklist — US-AUTO-41

## Scope Validation
- [ ] only allowed files changed
- [ ] no unrelated refactors introduced
- [ ] rollback lifecycle behavior was not weakened

## Functional Validation
- [ ] `automation/scripts/commit_story_artifacts.sh` exists
- [ ] script requires a story id argument
- [ ] script commits only allowed story artifact paths
- [ ] script fails when unrelated dirty files exist
- [ ] script fails when no eligible artifact changes exist
- [ ] `run_story.sh` blocks on dirty story artifacts
- [ ] remediation message points to the handoff script
- [ ] no implicit auto-commit exists in run flow

## Verification
- [ ] relevant tests pass
- [ ] docs updated
- [ ] epic registry updated
- [ ] operator flow is documented as `materialize -> commit -> run`

=== FILE: 05_followups.md ===
# Follow-ups — US-AUTO-41

## Follow-Up Prompt Queue
1. Add a helper to preview exact pending artifact paths before commit handoff.
2. Detect partially materialized story artifacts before commit.
3. Add a higher-level operator helper that chains materialize and commit when explicitly requested.
4. Add broader story lifecycle state introspection.
5. Revisit adjacent workflow friction around ledger artifacts if it remains visible after this handoff lands.

## Iteration Notes
Keep US-AUTO-41 narrow and contract-focused. Future UX polish should build on this explicit handoff rather than replacing it with hidden behavior.

=== FILE: 06_manual_actions.md ===
# Manual Actions — US-AUTO-41

## Required Human Actions
1. update the bundle pack
2. materialize the bundle
3. run the story workflow after implementation is prepared
4. review tests, docs, and registry updates
5. open PR and finalize via the standard US-AUTO flow

## Completion Status
Current state:
- bundle draft prepared
- validator corrections applied
- awaiting successful materialization

Expected future operator flow after implementation:
1. `new_story_bundle.sh <STORY_ID>`
2. materialize
3. `automation/scripts/commit_story_artifacts.sh <STORY_ID>`
4. `automation/scripts/run_story.sh <STORY_ID>`