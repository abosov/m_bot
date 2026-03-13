# US-AUTO-2: Run story launcher by STORY_ID

## Story ID and Title
- Story ID: `US-AUTO-2`
- Title: `Run story launcher by STORY_ID`

## Objective
Add a simple launcher script that starts the existing Codex pipeline by STORY_ID instead of requiring a master prompt file path.

## Scope
- Add `automation/scripts/run_story.sh`
- Resolve bundle path from `STORY_ID`
- Validate required bundle files before launch
- Invoke existing `automation/run_codex_task.sh` with the resolved `03_master_prompt.md`
- Add minimal documentation updates only if needed

## Non-goals
- No review-loop automation
- No auto-fix loop
- No changes to runtime Zumbot code
- No deploy / CI / GitHub Actions changes
- No replacement or refactor of `automation/run_codex_task.sh`

## Dependencies
- `US-AUTO-1` story bundle bootstrap automation
- Existing bundle structure under `automation/bundles/active/<STORY_ID>/`
- Existing runner `automation/run_codex_task.sh`

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `automation/run_codex_task.sh`

## Current Code Reality
- The current pipeline requires a prompt file path such as `automation/bundles/active/US-PAY-3/03_master_prompt.md`
- Story bundle creation is already automated by `automation/scripts/new_story_bundle.sh`
- There is no story-first launcher yet

## Target Architecture
- A user can run the existing pipeline by STORY_ID through a thin wrapper script
- The wrapper validates bundle completeness enough to prevent obvious bad launches
- The existing runner remains the execution engine and source of truth for actual run behavior

## Allowed Files
- `automation/scripts/**`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`

## Forbidden Files
- `automation/templates/**`
- `automation/run_codex_task.sh`
- `backend/**`
- `frontend/**`
- `.github/**`
- deploy / infra files

## Risks
- The launcher may become too smart and start duplicating logic already owned by `run_codex_task.sh`
- Bundle validation may become too strict or too weak

## Manual Actions
- Human still reviews generated diff and decides whether to merge
- Human still creates PR and runs any broader checks if needed

## Acceptance Notes
- Running `bash automation/scripts/run_story.sh US-AUTO-2` resolves the active bundle
- The script fails clearly if the story bundle or required prompt file is missing
- The script delegates execution to `automation/run_codex_task.sh`
- The script does not modify unrelated files or logic
