# US-AUTO-5 PROMPT 1 — Automatic AI review for Codex runs

## ROLE
You are the System Architect + Developer + Tech Writer + QA + Security Reviewer for Zumbot.

## TASK
Implement a thin script that resolves the latest run for a story, validates exiing review artifacts, and writes a standardized AI review result artifact into that run directory.

## MANDATORY CONTEXT
Read and follow:
- docs/90_codex/CODEX_OPERATING_SYSTEM.md
- docs/90_codex/PROJECT_CONTEXT.md
- docs/90_codex/REPOSITORY_MAP.md
- docs/90_codex/PROJECT_CONTEXT_UPDATE_PROTOCOL.md
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md
- docs/90_codex/REVIEW_CLASSIFICATION_RULES.md
- automation/scripts/review_story_run.sh
- automation/bundles/active/US-AUTO-5/00_story.md
- automation/bundles/active/US-AUTO-5/01_context_bundle.md
- automation/bundles/active/US-AUTO-5/02_file_scope.md

## GOAL
Add a script:

- `automation/scripts/ai_review_story_run.sh`

The script must:
1. accept `STORY_ID`
2. resolve the latest run directory for that story
3. fail clearly if no run exists
4. validate required review inputs exist in the latest run:
   - `review_bundle.md`
   - `chatgpt_review_prompt.md`
   - `diff.patch`
   - `changed_files.txt`
   - `pytest.txt`
5. write a standardized result artifact in the latest run directory, for example:
   - `ai_review_result.md`
6. the result artifact must include at minimum:
   - STORY_ID
   - latest run path
   - paths to the review input artifacts
   - a placeholder section for AI review verdict
   - a placeholder section for blocking findings
   - a placeholder section for non-blocking improvements
   - a placeholder section for recommended next step
7. print a concise operator message pointing to the result artifact

## NON-GOALS
Do not:
- modify `automation/run_codex_task.sh`
- execute automatic fixes
- modify runtime Zumbot code
- touch backend, frontend, deploy, infra, database, or `.github`
- add PR automation
- introduce unrelated refactors

## SOURCE OF TRUTH
- docs/90_codex/CODEX_OPERATING_SYSTEM.md
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md
- docs/90_codex/REVIEW_CLASSIFICATION_RULES.md
- automation/scripts/review_story_run.sh
- automation/bundles/active/US-AUTO-5/00_story.md
- automation/bundles/active/US-AUTO-5/01_context_bundle.md
- automation/bundles/active/US-AUTO-5/02_file_scope.md

## FILES ALLOWED TO CHANGE
- automation/scripts/ai_review_story_run.sh
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md

## FILES NOT ALLOWED TO CHANGE
- automation/run_codex_task.sh
- automation/templates/**
- backend/**
- frontend/**
- .github/**
- deployment / infrastructure files
- database migrations

## BEFORE IMPLEMENTING
1. identify exact files to change
2. explain how latest-run resolution will be handled
3. explain why this story records review results but does not execute fixes
4. state which layers are explicitly out of scope

## IMPLEMENTATION RULES
- minimal patch only
- no unrelated refactor
- no formatting-only edits
- keep the script a thin wrapper
- reuse existing review artifact assumptions
- use shell-safe patterns
- prefer clear operator UX and precise failure messages
- update docs only if behavior/process changes require it

## TEST PLAN
At minimum:
- shell syntax validation for the new script
- one successful invocation against a story with an existing run
- one failing invocation for a non-existent story id or no runs
- verify the standardized result artifact is written

## OUTPUT FORMAT
Return:
1. changed files summary
2. design rationale
3. validation performed
4. example command usage
5. risks / follow-ups
6. final diff
