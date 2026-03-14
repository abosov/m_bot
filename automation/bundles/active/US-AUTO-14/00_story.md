# US-AUTO-14: Allowed Files Guard

## Story ID and Title
- Story ID: `US-AUTO-14`
- Title: `Allowed Files Guard`

## Objective
Add a deterministic allowed-files guard that stops the Codex pipeline when the implementation changes files outside the scope explicitly declared in the active story bundle.

## Scope
- Add `automation/scripts/check_allowed_files.sh`.
- Parse the active story bundle file `02_file_scope.md`.
- Read the section `## Files Allowed To Change`.
- Support exact file paths and simple recursive wildcard patterns ending with `/**`.
- Compare the declared allowed paths against the actual changed files collected after Codex materialization.
- Fail fast if any changed file is outside the declared allowed scope.
- Integrate the guard into `automation/run_codex_task.sh` after worktree materialization and changed-files collection, but before pytest and downstream review steps.
- Add focused tests for the guard behavior.
- Update workflow docs/checklists only as needed for the new execution gate.

## Non-goals
- Do not add diff-size limits in this story.
- Do not add AI review gate logic in this story.
- Do not redesign story bundle validation structure.
- Do not change `finalize_story.sh`.
- Do not add background polling, retry loops, or GitHub Actions changes.
- Do not implement repository map injection changes here.

## Dependencies
- Existing bundle pack / materialization / validation flow.
- Existing `automation/run_codex_task.sh` execution flow with isolated worktree materialization.
- Existing active story bundles that define `02_file_scope.md`.
- Existing review / pytest artifact generation in the runner.

## Source of Truth
- `automation/run_codex_task.sh`
- `automation/scripts/run_story.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/bundles/active/US-AUTO-13/02_file_scope.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`

## Current Code Reality
- Story execution already validates the existence and structure of all seven bundle files before launching the runner.
- Bundle validation already requires `02_file_scope.md` to contain `## Files Allowed To Change` and `## Files Not Allowed To Change`.
- The runtime runner already materializes isolated worktree changes into the primary checkout and produces a deterministic changed-files artifact.
- There is currently no runtime scope enforcement after Codex writes changes, so Codex can still modify files outside the intended story boundary if they end up materialized into the main checkout.

## Target Outcome
- Every Codex story run is blocked if changed files exceed the explicit file scope declared by the story.
- The guard is deterministic, shell-based, and easy to audit.
- The failure message clearly shows which files violated scope.
- The runner fails before pytest / review if scope is violated.
- Allowed-files enforcement becomes a standard pipeline layer for all future stories.

