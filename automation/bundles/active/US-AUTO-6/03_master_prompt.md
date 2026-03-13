# US-AUTO-6 PROMPT 1 — AI review classification

## ROLE
You are the System Architect + Data Architect + UX + Developer + Tech Writer + QA + Security Reviewer for Zumbot.

## TASK
Implement a thin script that resolves the latest run for a story, validates the stored AI review artifact, executes a real AI classification command using that artifact plus the classification rules, and writes the resulting classification output into that run directory.

## MANDATORY CONTEXT
Read and follow:
- docs/90_codex/CODEX_OPERATING_SYSTEM.md
- docs/90_codex/PROJECT_CONTEXT.md
- docs/90_codex/REPOSITORY_MAP.md
- docs/90_codex/PROJECT_CONTEXT_UPDATE_PROTOCOL.md
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md
- docs/90_codex/REVIEW_CLASSIFICATION_RULES.md
- automation/scripts/ai_review_story_run.sh
- automation/bundles/active/US-AUTO-6/00_story.md
- automation/bundles/active/US-AUTO-6/01_context_bundle.md
- automation/bundles/active/US-AUTO-6/02_file_scope.md

## GOAL
Add a script:

- `automation/scripts/classify_review_story_run.sh`

The script must:
1. accept `STORY_ID`
2. resolve the latest run directory for that story
3. fail clearly if no run exists
4. validate the latest run already contains:
   - `ai_review_result.md`
5. execute a real AI classification command using:
   - `ai_review_result.md`
   - `docs/90_codex/REVIEW_CLASSIFICATION_RULES.md`
6. write the actual classification output to a durable result artifact in the latest run directory, for example:
   - `review_classification.md`
7. write the raw command output to a separate artifact if your design needs it
8. print a concise operator message pointing to the result artifact

## NON-GOALS
Do not:
- modify `automation/run_codex_task.sh`
- execute automatic fixes
- modify runtime Zumbot code
- touch backend, frontend, deploy, infra, database, or `.github`
- add PR automation
- introduce unrelated refactors
- generate a placeholder-only artifact with `TBD` sections instead of executing classification

## SOURCE OF TRUTH
- docs/90_codex/CODEX_OPERATING_SYSTEM.md
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md
- docs/90_codex/REVIEW_CLASSIFICATION_RULES.md
- automation/scripts/ai_review_story_run.sh
- automation/bundles/active/US-AUTO-6/00_story.md
- automation/bundles/active/US-AUTO-6/01_context_bundle.md
- automation/bundles/active/US-AUTO-6/02_file_scope.md

## FILES ALLOWED TO CHANGE
- automation/scripts/classify_review_story_run.sh
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md
- automation/bundles/active/US-AUTO-6/**
- tests/test_review_classification_script.py

## FILES NOT ALLOWED TO CHANGE
- automation/run_codex_task.sh
- automation/templates/**
- backend/**
- frontend/**
- .github/**
- deployment / infrastructure files
- database migrations

## IMPLEMENTATION RULES
- minimal patch only
- no unrelated refactor
- no formatting-only edits
- keep the script a thin wrapper
- reuse existing AI review artifact assumptions
- prefer clear operator UX and precise failure messages
- update docs only when behavior/process changes require it

## TEST PLAN
- `pytest tests/test_review_classification_script.py`

## OUTPUT FORMAT
Return:
1. changed files summary
2. rationale
3. test results
4. risks/follow-ups
5. final diff
