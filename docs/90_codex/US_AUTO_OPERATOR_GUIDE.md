# US-AUTO Operator Guide

This guide is the operator-facing workflow contract for the US-AUTO story pipeline.

## Normal workflow

1. Confirm the pre-story gate is satisfied.
2. Run `automation/scripts/run_story.sh <STORY_ID>`.
3. Analyze the pinned run with `AUTOMATION_RUN_DIR`.
4. Follow the single operator decision from analyze.
5. Continue through AI review, classification, review gate, merge review, PR merge, cleanup, local `main` update, and registry closeout.

## Pre-story gate

Before starting a story:

- work from a non-`main` branch;
- make sure the working tree is clean unless the current story explicitly requires a documented continuation state;
- confirm the previous story is fully closed, not just merged;
- confirm the registry does not still require a closeout action for the previous story.

## run_story stage

Run:

```bash
automation/scripts/run_story.sh <STORY_ID>
```

`run_story.sh` creates a run directory under `automation/runs/<STORY_ID>/...`. Treat that directory as pinned evidence for later analyze/review steps.

## analyze stage

Analyze is mandatory before deciding to rerun, review, classify, gate, or stop.

Analyze reports:

- the pinned run directory;
- artifact presence;
- committed-HEAD evidence checks;
- review-stage readiness;
- rerun gates;
- workflow chaining details;
- an operator decision section;
- the final run status line.

If multiple raw status lines appear to point in different directions, follow the single `Required next action` from the operator decision block. Do not infer a different next step from a later-stage artifact alone.
Any new commit after a pinned run invalidates the normal review path for that run unless analyze explicitly confirms the exact manual-finish continuation path.

## Correct analyze_story_run.sh command contract

`analyze_story_run.sh` receives the run directory through `AUTOMATION_RUN_DIR`.

Correct:

```bash
AUTOMATION_RUN_DIR=automation/runs/<STORY_ID>/<RUN_DIR> automation/scripts/analyze_story_run.sh <STORY_ID>
```

Incorrect:

```bash
automation/scripts/analyze_story_run.sh <STORY_ID> automation/runs/<STORY_ID>/<RUN_DIR>
```

The run directory is not accepted as a second positional argument.

## Operator decision model after analyze

Read the `OPERATOR DECISION` block first.

Use it as the single next-action summary:

- `Current state` tells you which stage is active.
- `Required next action` is the only action to take next.
- `Allowed actions` lists safe continuations from that exact state.
- `Forbidden actions` lists actions that would break the workflow contract.
- `Why` explains the blocker or readiness condition.

If the operator decision conflicts with an operator guess, the decision block wins.
If `Next recommended command` and a blocker both appear, the blocker still wins unless `Required next action` explicitly tells you to run that command now.
`next_step.sh` is not the decision authority for this story. Treat it as a follow-up idea, not as permission to override analyze.

## Dirty tree handling

A dirty tree blocks review-stage actions even if AI review, classification, or gate artifacts already exist.

If analyze says the tree is dirty:

- commit the workspace changes; or
- discard the workspace changes; then
- rerun analyze on the same pinned run.

Do not run review, AI review, classification, or review gate with workspace-only changes present.

## Rerun required cases

Rerun `run_story.sh` when analyze shows one of these states:

- stale run evidence after HEAD moved and no manual-finish continuation applies;
- codex failure;
- materialization failure;
- pytest failure;
- missing or unusable run artifacts that require a fresh run;
- review artifact fidelity mismatch that invalidates the pinned run surface.

After rerun, analyze the new pinned run with `AUTOMATION_RUN_DIR`.

## Rerun forbidden cases

Do not rerun `run_story.sh` when analyze shows one of these states:

- `blocked_non_converging_rerun`;
- `blocked_manual_finish_final_head_unproven`;
- `manual_finish_ready_for_review`;
- a manual-finish continuation with rerun gate marked forbidden;
- dirty tree only, where commit/discard is the required action instead;
- a later review-stage artifact is invalid but the required action is to rerun that stage on the same pinned run.

If analyze says rerun is forbidden, follow the pinned-run continuation path instead.

## Implementation freeze / refresh path (US-AUTO-60)

Use this path only when implementation is already accepted on the current committed HEAD and you need fresh review evidence without rerunning Codex implementation.

Run:

```bash
AUTOMATION_REFRESH_PYTEST_CMD="python3 -m pytest <story-scoped-tests>" automation/scripts/refresh_review_evidence.sh <STORY_ID>
AUTOMATION_RUN_DIR=automation/runs/<STORY_ID>/<REFRESH_RUN_DIR> automation/scripts/analyze_story_run.sh <STORY_ID>
```

Required preconditions:

- branch is not `main`;
- working tree is clean;
- active story bundle exists for `<STORY_ID>`.

Forbidden uses:

- replacing normal implementation work (`run_story.sh` remains the implementation path);
- running refresh on `main`;
- running refresh with a dirty tree;
- reusing refreshed evidence after any new commit (it becomes stale and must be refreshed again).

Refresh does not close the story. Review-stage still requires clean tree + valid pinned evidence and the usual AI review, classification, and review gate sequence.

## Manual-finish continuation

Manual finish exists only for the explicit non-converging rerun path.

Safe sequence:

1. Analyze reports `blocked_non_converging_rerun`.
2. Finish the story manually in the workspace.
3. Commit the manual finish.
4. Re-run analyze on the same pinned run.
5. If analyze reports `blocked_manual_finish_final_head_unproven`, refresh the pinned review artifacts and analyze again on the same run.
6. Continue review only if analyze validates the manual-finish continuation and final-HEAD compliance.

Do not rerun `run_story.sh` between steps 1 and 6.

## Review-stage path

When analyze says review-stage is allowed:

- use the pinned run through `AUTOMATION_RUN_DIR`;
- run the exact next command shown by analyze;
- rerun analyze after each review-stage step if you want a refreshed decision summary.

Review-stage is allowed only on a clean committed HEAD or on the exact validated manual-finish continuation path.
Review-stage is still blocked if the tree is dirty, the pinned run is stale, or final-HEAD compliance is not yet proven for a manual-finish continuation.

## AI review, classification, and review gate path

Normal path:

1. `ai_review_story_run.sh`
2. `classify_review_story_run.sh`
3. `review_gate_story_run.sh`

Always use the pinned run:

```bash
AUTOMATION_RUN_DIR=automation/runs/<STORY_ID>/<RUN_DIR> automation/scripts/ai_review_story_run.sh <STORY_ID>
AUTOMATION_RUN_DIR=automation/runs/<STORY_ID>/<RUN_DIR> automation/scripts/classify_review_story_run.sh <STORY_ID>
AUTOMATION_RUN_DIR=automation/runs/<STORY_ID>/<RUN_DIR> automation/scripts/review_gate_story_run.sh <STORY_ID>
```

Do not skip directly to a later stage when analyze says the current stage artifact is missing or invalid.
If classification rejects or the review gate rejects, do not continue as if approval exists. Fix the implementation and rerun from committed HEAD, or use the existing escalation workflow if analyze tells you escalation is required.

## Post-merge registry closure gate

PR merged is not story closed.

Story closed requires:

1. PR merged.
2. Branch cleanup done.
3. `main` updated locally.
4. Registry checked.
5. Registry updated or explicitly confirmed not required.

Do not start the next story until this closure gate is complete.
`next_step.sh` remains a follow-up, not the closure authority for this story.

## Anti-patterns

- Passing the run directory as a second positional argument to `analyze_story_run.sh`.
- Skipping analyze after `run_story.sh`.
- Treating `RUN STATUS` or a convenient next command as permission to ignore dirty-tree or committed-HEAD checks.
- Rerunning `run_story.sh` during a manual-finish continuation.
- Running review/classify/gate on workspace-only changes.
- Treating PR merge as automatic story closure.
- Starting the next story before branch cleanup, local `main` update, and registry closeout.
- Expecting `next_step.sh` to replace operator judgment in this story. It remains a follow-up, not the current contract.

## Examples

Normal analyze:

```bash
AUTOMATION_RUN_DIR=automation/runs/US-AUTO-77/2026-05-02_12-00-00 automation/scripts/analyze_story_run.sh US-AUTO-77
```

Normal gate path:

```bash
AUTOMATION_RUN_DIR=automation/runs/US-AUTO-77/2026-05-02_12-00-00 automation/scripts/review_gate_story_run.sh US-AUTO-77
```

Manual-finish continuation:

```bash
# analyze says blocked_non_converging_rerun
# finish manually, commit, then analyze the same pinned run again
AUTOMATION_RUN_DIR=automation/runs/US-AUTO-77/2026-05-02_12-00-00 automation/scripts/analyze_story_run.sh US-AUTO-77
```

Post-merge closeout reminder:

```text
PR merged != story closed
story closed = merge + branch cleanup + local main update + registry check/closeout
```

Wrong analyze invocation:

```bash
automation/scripts/analyze_story_run.sh US-AUTO-77 automation/runs/US-AUTO-77/2026-05-02_12-00-00
```

Wrong post-merge assumption:

```text
PR merged
therefore story closed
```
