# US-AUTO-5: Automatic AI review for Codex runs

## Story ID and Title
- Story ID: `US-AUTO-5`
- Title: `Automatic AI review for Codex runs`

## Objective
Add a thin automation step that prepares and records a standardized AI review result for the latest Codex run of a story.

## Scope
- Add `automation/scripts/ai_review_story_run.sh`
- Resolve latest run for `STORY_ID`
- Reuse existing review artifacts from that run
- Produce a review result artifact in the run directory
- Keep behavior lightweight and deterministic
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
- Final review judgment is still manual and not stored as a standardized run artifact

## Target Architecture
- Add a thin AI-review launcher by `STORY_ID`
- Resolve the latest run and required review artifacts
- Store a standardized AI review result artifact in that run directory
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
- Poor artifact naming could make runs harder to audit
- The script must stay a thin wrapper and not duplicate generation logic

## Manual Actions
- Human still decides whether findings are blockers or acceptable risk
- Human still chooses whether to merge or request follow-up changes

## Acceptance Notes
- Running the AI review launcher by `STORY_ID` resolves the latest run
- The script fails clearly if no run exists or required review artifacts are missing
- The script creates a standardized AI review result artifact in the latest run directory
