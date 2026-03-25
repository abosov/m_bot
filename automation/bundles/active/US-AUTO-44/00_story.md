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

