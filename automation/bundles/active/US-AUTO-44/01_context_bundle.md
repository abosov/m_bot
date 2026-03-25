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

