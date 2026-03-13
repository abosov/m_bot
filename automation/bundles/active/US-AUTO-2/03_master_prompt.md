# US-AUTO-2 PROMPT 1 — Run story launcher by STORY_ID

## ROLE
You are the System Architect + Developer + Tech Writer + QA + Security Reviewer for Zumbot.

## TASK
Implement a thin launcher script that starts the existing Codex pipeline by STORY_ID instead of requiring a direct master prompt file path.

## MANDATORY CONTEXT
Read and follow:
- docs/90_codex/CODEX_OPERATING_SYSTEM.md
- docs/90_codex/PROJECT_CONTEXT.md
- docs/90_codex/REPOSITORY_MAP.md
- docs/90_codex/PROJECT_CONTEXT_UPDATE_PROTOCOL.md
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md
- docs/90_codex/STORY_BUNDLE_SPEC.md
- automation/run_codex_task.sh
- automation/scripts/new_story_bundle.sh
- automation/bundles/active/US-AUTO-2/00_story.md
- automation/bundles/active/US-AUTO-2/01_context_bundle.md
- automation/bundles/active/US-AUTO-2/02_file_scope.md

## GOAL
Add a script:

- `automation/scripts/run_story.sh`

The script must:
1. accept `STORY_ID` as the primary input
2.esolve the active bundle directory:
   - `automation/bundles/active/<STORY_ID>/`
3. verify that the bundle exists
4. verify that `03_master_prompt.md` exists
5. perform lightweight validation for the required bundle files:
   - `00_story.md`
   - `01_context_bundle.md`
   - `02_file_scope.md`
   - `03_master_prompt.md`
   - `04_review_checklist.md`
   - `05_followups.md`
   - `06_manual_actions.md`
6. invoke the existing runner:
   - `automation/run_codex_task.sh <resolved master prompt path>`
7. print clear error messages for missing story bundle or missing required files

## NON-GOALS
Do not:
- modify `automation/run_codex_task.sh`
- create a new pipeline controller
- add review-loop automation
- add auto-fix loop logic
- modify runtime Zumbot code
- touch backend, frontend, deploy, infra, database, or `.github`
- introduce broad refactors

## SOURCE OF TRUTH
- docs/90_codex/CODEX_OPERATING_SYSTEM.md
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md
- docs/90_codex/STORY_BUNDLE_SPEC.md
- automation/run_codex_task.sh
- automation/scripts/new_story_bundle.sh
- automation/bundles/active/US-AUTO-2/00_story.md
- automation/bundles/active/US-AUTO-2/01_context_bundle.md
- automation/bundles/active/US-AUTO-2/02_file_scope.md

## FILES ALLOWED TO CHANGE
- automation/scripts/run_story.sh
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
3. state how bundle validation will remain lightweight
4. state which layers are explicitly out of scope

## IMPLEMENTATION RULES
- minimal patch only
- no unrelated refactor
- no formatting-only edits
- keep the launcher a thin wrapper
- do not duplicate execution logic already owned by `run_codex_task.sh`
- use shell-safe patterns
- prefer understandable CLI UX and clear failures
- update docs only if behavior/process changes require it

## TEST PLAN
At minimum:
- shell syntax validation for the new script
- one successful invocation against an existing story bundle
- one failing invocation for a missing or invalid story id
- one failing invocation for a missing required file, if easy to validate safely

## OUTPUT FORMAT
Return:
1. changed files summary
2. design rationale
3. validation performed
4. example command usage
5. risks / follow-ups
6. final diff
