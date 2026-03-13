# US-AUTO-4: Lean story context for Codex runs

## Story ID and Title
- Story ID: `US-AUTO-4`
- Title: `Lean story context for Codex runs`

## Objective
Reduce Codex input size by defaulting the runner to a lean story context while keeping an explicit full-context mode available.

## Scope
- Update `automation/run_codex_task.sh`
- Add a default lean context mode for Codex input
- Add an explicit full-context flag
- Log which bundle files were included in the generated story context
- Update docs only if required

## Non-goals
- No runtime Zumbot code changes
- No changes to backend, frontend, deploy, infra, or database
- No AI review automation in this story
- No change to bundle file structure
- No change to `new_story_bundle.sh`, `run_story.sh`, or `review_story_run.sh` unless strictly necessary

## Dependencies
- Existing bundle structure under `automation/bundles/active/<STORY_ID>/`
- Existing runner `automation/run_codex_task.sh`

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `automation/run_codex_task.sh`

## Current Code Reality
- The runner currently builds a story context from the active bundle before invoking Codex
- The current approach likely includes more bundle content than most implementation runs need
- This increases token usage, prompt noise, and scope-creep risk

## Target Architecture
- Default mode includes only the minimal files needed for most implementation runs
- Full bundle context remains available through an explicit flag
- The runner records which files were included in the context sent to Codex

## Allowed Files
- `automation/run_codex_task.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`

## Forbidden Files
- `automation/templates/**`
- `automation/scripts/new_story_bundle.sh`
- `automation/scripts/run_story.sh`
- `automation/scripts/review_story_run.sh`
- `backend/**`
- `frontend/**`
- `.github/**`
- deployment / infrastructure files
- database migrations

## Risks
- Lean mode may omit context needed by some stories
- Full-context mode must remain available and explicit
- Context-file logging must not break the current run flow

## Manual Actions
- Human still decides when a story needs full context
- Human still reviews Codex output and artifacts

## Acceptance Notes
- Default runner behavior uses lean context
- A full-context flag is available and works
- The run artifacts clearly show which context files were included
