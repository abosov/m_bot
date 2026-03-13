# US-AUTO-6: AI review classification

## Story ID and Title
- Story ID: `US-AUTO-6`
- Title: `AI review classification`

## Objective
Add a thin automation step that classifies the stored AI review findings for the latest story run and writes the classification result as a durable run artifact.

## Scope
- Add `automation/scripts/classify_review_story_run.sh`
- Resolve the latest run for `STORY_ID`
- Reuse the existing `ai_review_result.md` artifact and classification rules
- Execute a real AI classification step using those inputs
- Persist the classification output as a run artifact
- Update docs only if required

## Non-goals
- No automatic code fixes after classification
- No modification of `automation/run_codex_task.sh`
- No changes to runtime Zumbot code
- No CI / deploy / GitHub Actions changes
- No PR automation in this story

## Dependencies
- Existing run artifact structure under `automation/runs/<STORY_ID>/<RUN_ID>/`
- Existing AI review artifact produced by `automation/scripts/ai_review_story_run.sh`
- Existing classification rules in `docs/90_codex/REVIEW_CLASSIFICATION_RULES.md`

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/REVIEW_CLASSIFICATION_RULES.md`
- `automation/scripts/ai_review_story_run.sh`

## Current Code Reality
- Runs can already store a durable `ai_review_result.md` artifact for the latest story run
- The process checklist requires classification, but there is no script that executes and stores a standardized classification output
- The active `US-AUTO-6` bundle is still template-only and does not yet constrain the implementation

## Target Architecture
- Add one thin classifier launcher by `STORY_ID`
- Resolve the latest run and require the existing AI review artifact
- Execute a real classification command using the AI review output plus the classification rules
- Store the actual classification output in the run directory for auditability
- Keep remediation decisions outside the automation step

## Allowed Files
- `automation/scripts/classify_review_story_run.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `automation/bundles/active/US-AUTO-6/**`
- `tests/test_review_classification_script.py`

## Forbidden Files
- `automation/run_codex_task.sh`
- `automation/templates/**`
- `backend/**`
- `frontend/**`
- `.github/**`
- deployment / infrastructure files
- database migrations

## Risks
- Classification automation may overreach into remediation guidance; keep the script output-only and do not trigger fixes
- Poor artifact naming could make audit trails ambiguous; use stable run-local filenames
- If the prior AI review artifact is missing, the script must fail clearly instead of guessing

## Manual Actions
- Human still decides whether to merge, request follow-up fixes, or defer work
- Human still executes follow-up prompts for accepted blockers or improvements

## Acceptance Notes
- Running the classifier by `STORY_ID` resolves the latest run
- The script fails clearly if no run exists or if `ai_review_result.md` is missing
- The script executes a real AI classification command
- The script stores the resulting classification output as a durable artifact in the latest run directory
