# US-AUTO-10: Context Bundle

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `automation/run_codex_task.sh`
- `tests/test_run_codex_task.py`

## Current Code Reality
- `automation/run_codex_task.sh` creates a detached temporary git worktree from the current branch `HEAD`, runs Codex inside it, and cleans it up on exit.
- The current script collects git artifacts and runs pytest from the primary checkout without first materializing isolated-worktree file changes, which can report a false-positive successful run.
- Existing tests cover isolated execution and worktree cleanup, but they do not enforce a materialization invariant back to the primary checkout.

## Target Architecture
- The runner keeps isolated execution but adds a post-Codex materialization phase before pytest and artifact collection.
- Tracked diffs are applied into the primary checkout, regular untracked files are copied over, and the runner verifies the result path-by-path.
- Artifact generation must reflect the materialized primary checkout state instead of silently ignoring isolated-only output.

## Risks
- The implementation assumes a clean primary checkout at run start; this is already a runner precondition and keeps patch application deterministic.
- Untracked non-regular filesystem objects are out of scope; the story only requires normal tracked files and regular untracked files.

## Acceptance Notes
- Targeted tests prove tracked edits, untracked files, non-zero Codex exit behavior, explicit failure on materialization miss, and artifact alignment.
- The checklist update records that pytest and artifact collection happen only after successful materialization into the primary checkout.
