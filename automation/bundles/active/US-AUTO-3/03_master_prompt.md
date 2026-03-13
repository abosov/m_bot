# US-AUTO-3 PROMPT 1 — Review story run artifacts

## ROLE
You are the System Architect + Developer + Tech Writer + QA + Security Reviewer for Zumbot.

## TASK
Implement a thin review launcher that resolves the latest run artifacts for a STORY_ID and prepares a consistent review-orientedtep from existing generated files.

## MANDATORY CONTEXT
Read and follow:
- docs/90_codex/CODEX_OPERATING_SYSTEM.md
- docs/90_codex/PROJECT_CONTEXT.md
- docs/90_codex/REPOSITORY_MAP.md
- docs/90_codex/PROJECT_CONTEXT_UPDATE_PROTOCOL.md
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md
- docs/90_codex/STORY_BUNDLE_SPEC.md
- automation/run_codex_task.sh
- automation/scripts/run_story.sh
- automation/bundles/active/US-AUTO-3/00_story.md
- automation/bundles/active/US-AUTO-3/01_context_bundle.md
- automation/bundles/active/US-AUTO-3/02_file_scope.md

## GOAL
Add a script:

- `automation/scripts/review_story_run.sh`

The script must:
1. accept `STORY_ID` as the primary input
2. resolve the story run root:
   - `automation/runs/<STORY_ID>/`
3. fail clearly if the story run root does not exist
4. resolve the latest run directory for that story
5. fail clearly if no run directories exist
6. validate that required review artifacts exist in the latest run:
   - `review_bundle.md`
   - `chatgpt_review_prompt.md`
   - `diff.patch`
   - `changed_files.txt`
   - `pytest.txt`
7. print a concise review summary that includes:
   - STORY_ID
   - latest run path
   - required artifact paths
8. print a clear next-step instruction for the operator to review the generated artifacts
9. keep behavior lightweight and shell-safe

## NON-GOALS
Do not:
- modify `automation/run_codex_task.sh`
- regenerate review artifacts
- add auto-fix loop logic
- add PR automation
- modify runtime Zumbot code
- touch backend, frontend, deploy, infra, database, or `.github`
- introduce broad refactors

## SOURCE OF TRUTH
- docs/90_codex/CODEX_OPERATING_SYSTEM.md
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md
- docs/90_codex/STORY_BUNDLE_SPEC.md
- automation/run_codex_task.sh
- automation/scripts/run_story.sh
- automation/bundles/active/US-AUTO-3/00_story.md
- automation/bundles/active/US-AUTO-3/01_context_bundle.md
- automation/bundles/active/US-AUTO-3/02_file_scope.md

## FILES ALLOWED TO CHANGE
- automation/scripts/review_story_run.sh
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
2. state why `run_codex_task.sh` must remain unchanged
3. state how latest-run resolution will work
4. state which layers are explicitly out of scope

## IMPLEMENTATION RULES
- minimal patch only
- no unrelated refactor
- no formatting-only edits
- keep the launcher a thin wrapper
- do not duplicate artifact-generation logic already owned by `run_codex_task.sh`
- use shell-safe patterns
- prefer clear operator UX and precise failure messages
- update docs only if behavior/process changes require it

## TEST PLAN
At minimum:
- shell syntax validation for the new script
- one successful invocation against an existing story with runs
- one failing invocation for a story with no runs
- one failing invocation for a missing required artifact, if easy to validate safely

## OUTPUT FORMAT
Return:
1. changed files summary
2. design rationale
3. validation performed
4. example command usage
5. risks / follow-ups
6. final diff
