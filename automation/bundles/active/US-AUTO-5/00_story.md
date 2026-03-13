# US-AUTO-5: Automatic AI review for Codex runs

## Story ID and Title
- Story ID: `US-AUTO-5`
- Title: `Automatic AI review for Codex runs`

## Objective
Add a thin automation step that executes an AI review workflow for the latest Codex run of a story and stores the review result as a durable run artifact.

## Scope
- Add `automation/scripts/ai_review_story_run.sh`
- Resolve latest run for `STORY_ID`
- Reuse existing review artifacts from that run
- Execute an AI review step using existing review inputs
- Persist the AI review output as a run artifact
- Update docs only if required

## Non-goals
- No auto-fix loop
- No automatic code changes after review
- No modification of `automation/run_codex_task.sh`
- No runtime Zumbot code changes
- No CI / deploy / GitHub Actions changes
- No PR automation in this story

## Dependencies
- Existing run artifact structure under `automation/runs/<STORY_ID>/<RUN_ID>/`
- Existing review artifacts produced by `run_codex_task.sh`
- Existing review launcher `automation/scripts/review_story_run.sh`

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/REVIEW_CLASSIFICATION_RULES.md`
- `automation/scripts/review_story_run.sh`

## Current Code Reality
- Runs already produce `review_bundle.md` and `chatgpt_review_prompt.md`
- Review artifacts can be located for the latest run via `review_story_run.sh`
- There is no script that executes a standardized AI review step and stores the resulting output as a durable run artifact

## Target Architecture
- Add a thin AI-review launcher by `STORY_ID`
- Resolve the latest run and required review artifacts
- Execute a review command using the existing review prompt/input artifacts
- Store the AI review output in the run directory for auditability
- Keep human decision-making in the loop

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
- Review automation may overreach into fix automation
- The script may produce a wrapper artifact without actually executing review
- Poor artifact naming could make runs harder to audit

## Manual Actions
- Human still decides whether findings are blockers or acceptable risk
- Human still chooses whether to merge or request follow-up changes

## Acceptance Notes
- Running the AI review launcher by `STORY_ID` resolves the latest run
- The script fails clearly if no run exists or required review artifacts are missing
- The script executes a real AI review command
- The script stores the resulting AI review output as a durable artifact in the latest run directory
