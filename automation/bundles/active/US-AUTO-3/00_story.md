# US-AUTO-3: Review story run artifacts

## Story ID and Title
- Story ID: `US-AUTO-3`
- Title: `Review story run artifacts`

## Objective
Add a thin review launcher that takes a STORY_ID, finds the latest run artifacts for that story, and prepares a consistent review step from existing generated files.

## Scope
- Add `automation/scripts/review_story_run.sh`
- Resolve latest run directory under `automation/runs/<STORY_ID>/`
- Validate required review artifacts exist
- Print clear guidance and paths for review execution
- Reuse already generated run artifacts instead of inventing a new review format
- Add minimal documentation updates only if needed

## Non-goals
- No auto-fix loop
- No automatic code changes after review
- No modification of `automation/run_codex_task.sh`
- No runtime Zumbot code changes
- No CI / deploy / GitHub Actions changes
- No PR automation in this story

## Dependencies
- `US-AUTO-1` bundle bootstrap automation
- `US-AUTO-2` story launcher by STORY_ID
- Existing run artifact structure under `automation/runs/<STORY_ID>/<RUN_ID>/`

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `automation/run_codex_task.sh`

## Current Code Reality
- `automation/run_codex_task.sh` already generates review-related artifacts such as `review_bundle.md` and `chatgpt_review_prompt.md`
- Review is still performed manually after the run
- There is no story-first command that locates the latest run and launches a review-oriented step

## Target Architecture
- A user can review the latest run for a story by STORY_ID through a thin wrapper script
- The wrapper reuses the latest existing run artifacts instead of duplicating generation logic
- `run_codex_task.sh` remains the source of truth for artifact generation

## Allowed Files
- `automation/scripts/**`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`

## Forbidden Files
- `automation/run_codex_task.sh`
- `automation/templates/**`
- `backend/**`
- `frontend/**`
- `.github/**`
- deployment / infrastructure files
- database migrations

## Risks
- The review launcher may start duplicating artifact-generation logic that belongs to `run_codex_task.sh`
- It may guess the wrong run if latest-run resolution is sloppy
- Poor error handling could make review harder instead of easier

## Manual Actions
- Human still reads the review output and decides what to fix or merge
- Human still decides whether a finding is blocker, minor improvement, or follow-up story

## Acceptance Notes
- Running the review launcher by STORY_ID resolves the latest run for that story
- The script fails clearly if no run exists
- The script fails clearly if required review artifacts are missing
- The script reuses existing generated artifacts rather than regenerating them
