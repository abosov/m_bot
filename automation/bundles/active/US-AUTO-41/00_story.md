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

