# US-AUTO-38: Automatic rollback after failed automation run

## Story ID and Title
- Story ID: `US-AUTO-38`
- Title: `Automatic rollback after failed automation run`

## Objective
Introduce a deterministic automatic rollback contract for automation story runs so that any failed or interrupted run returns the repository working tree to the exact clean pre-run state without manual operator cleanup, while preserving the ephemeral automation paths contract established in US-AUTO-37.

## Scope
- Define the canonical failed-run rollback contract for automation story execution.
- Make rollback apply only when execution starts from a clean tree.
- Centralize rollback lifecycle ownership in the top-level orchestration layer.
- Restore tracked changes to the pre-run baseline on failed execution.
- Clean run-owned untracked artifacts created during failed execution.
- Preserve success behavior so intended story changes remain after a successful run.
- Add focused tests for success, failure, interruption/simulated trap behavior, and rollback-failure surfacing.
- Update workflow docs/checklists so failed-run semantics are explicit and auditable.

## Non-goals
- Do not redesign finalize flow.
- Do not introduce hidden stash-based recovery by default.
- Do not support rollback when the operator starts from a dirty tree.
- Do not redesign the story registry or broader ledger model.
- Do not expand this story into unrelated review gate, deployment, or budget-control work.

## Dependencies
- US-AUTO-37 ephemeral automation paths contract.
- Existing story bundle materialization/validation workflow.
- Existing execution wrappers:
  - `automation/scripts/run_story.sh`
  - `automation/run_codex_task.sh`
- Existing execution docs and checklist flow.

## Source of Truth
- `automation/scripts/run_story.sh`
- `automation/run_codex_task.sh`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- existing tests covering story execution behavior
- merged US-AUTO-37 behavior

## Current Code Reality
- US-AUTO-37 removed a class of false dirty-tree problems caused by ephemeral automation paths.
- Ephemeral cleanup is more consistent, but failed execution can still leave partial repository mutations behind.
- Current failure handling is not yet defined as a deterministic restore-to-baseline contract.
- Success and failure boundaries are not explicit enough for rollback ownership and diagnostics.

## Target Outcome
- Failed automation runs restore the exact clean pre-run repository state automatically.
- Successful runs preserve intended working tree changes.
- Rollback lifecycle ownership is centralized and explicit.
- Interrupted runs are treated as failures where supported.
- US-AUTO-37 behavior remains intact and regression-tested.

## Atomic Task Isolation Contract
- Single purpose: add deterministic automatic rollback for failed automation runs.
- Exact intent: restore the repository to its clean pre-run baseline after any supported failed or interrupted execution path.
- Out of scope:
  - finalize redesign,
  - broader registry/ledger redesign,
  - unrelated review/deploy changes.
- Allowed file boundary is defined in this bundle and must be enforced strictly.
- Forbidden file/area boundary is defined in this bundle and must be treated as a hard stop.
- Hard-stop condition: if implementation requires broader workflow redesign outside failed-run rollback semantics, stop and capture that work as a follow-up.

