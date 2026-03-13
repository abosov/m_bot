US-AUTO-1 PROMPT 1 — Add story bundle bootstrap script

## ROLE
You are the System Architect + Developer + Tech Writer + QA + Security Reviewer for Zumbot.

## TASK
Implement the first automation bootstrap step for the Codex workflow:
add a script that creates a new active story bundle from reusable templates.

## MANDATORY CONTEXT
Read and follow:
- docs/90_codex/CODEX_OPERATING_SYSTEM.md
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md
- docs/90_codex/STORY_BUNDLE_SPEC.md
- automation/run_codex_task.sh
- automation/templates/story_bundle_template.md
- automation/templates/codex_master_prompt_template.md
- automation/templates/followup_prompt_template.md
- automation/templates/review_prompt_template.md
- automation/templates/pr_description_template.md

## GOAL
Add a script:

- automation/scripts/new_story_bundle.sh

The script must:
1. accept:
   - STORY_ID
   - STORY_TITLE
2. create:
   - automation/bundles/active/<STORY_ID>/
3. generate:
   - 00_story.md
   - 01_context_bundle.md
   - 02_file_scope.md
   -3_master_prompt.md
   - 04_review_checklist.md
   - 05_followups.md
   - 06_manual_actions.md
4. prefill the files with stable sections and readable placeholders
5. fail if the target bundle already exists
6. validate STORY_ID format
7. be safe/idempotent in the sense that it does not overwrite an existing story bundle

## NON-GOALS
Do not:
- change runtime billing logic
- change backend/api, services, database, migrations, frontend
- add review loop automation
- modify deployment, CI/CD, or .github
- refactor automation/run_codex_task.sh in this prompt
- implement branch creation in this prompt
- add unrelated scripts

## SOURCE OF TRUTH
- docs/90_codex/CODEX_OPERATING_SYSTEM.md
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md
- docs/90_codex/STORY_BUNDLE_SPEC.md
- existing automation templates under automation/templates/
- existing runner expectations in automation/run_codex_task.sh

## FILES ALLOWED TO CHANGE
- automation/scripts/**
- automation/templates/**
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md
- docs/90_codex/STORY_BUNDLE_SPEC.md

## FILES NOT ALLOWED TO CHANGE
- automation/run_codex_task.sh
- backend/**
- frontend/**
- database.py
- scripts/migrations/**
- .github/**
- deploy / infra /**
- unrelated tests

## BEFORE IMPLEMENTING
1. identify exact existing files to modify
2. identify exact templates to reuse
3. state source of truth
4. state which files/layers must not be changed

## IMPLEMENTATION RULES
- minimal patch only
- no unrelated refactor
- no formatting-only edits
- no new files unless strictly necessary
- prefer shell-safe implementation
- prefer reusing existing templates over duplicating content
- generated markdown should stay easy for a human to edit
- if template placeholders are improved, keep them generic and reusable

## EXPECTED DESIGN
Preferred behavior:
- script reads reusable templates where practical
- script fills STORY_ID and STORY_TITLE
- script creates all 7 bundle files in the active story folder
- script prints a short success summary with created paths
- script exits non-zero on invalid input or existing bundle

## TESTING
At minimum:
- validate shell syntax
- provide example invocation/output in the final response
- if repository already has a matching pattern for script/tool tests, use it
- otherwise keep verification lightweight and focused

## OUTPUT FORMAT
Return:
1. changed files summary
2. design rationale
3. validation performed
4. example command to create a new story bundle
5. risks / follow-ups
6. final diff
