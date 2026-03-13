# US-AUTO-4 PROMPT 1 — Lean story context for Codex runs

## ROLE
You are the System Architect + Developer + Tech Writer + QA + Security Reviewer for Zumbot.

## TASK
Implement lean story context mode in the Codex runner so default runs includenly the minimal bundle files needed for most implementation tasks, while keeping full context available via explicit flag.

## MANDATORY CONTEXT
Read and follow:
- docs/90_codex/CODEX_OPERATING_SYSTEM.md
- docs/90_codex/PROJECT_CONTEXT.md
- docs/90_codex/REPOSITORY_MAP.md
- docs/90_codex/PROJECT_CONTEXT_UPDATE_PROTOCOL.md
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md
- docs/90_codex/STORY_BUNDLE_SPEC.md
- automation/run_codex_task.sh
- automation/bundles/active/US-AUTO-4/00_story.md
- automation/bundles/active/US-AUTO-4/01_context_bundle.md
- automation/bundles/active/US-AUTO-4/02_file_scope.md

## GOAL
Update `automation/run_codex_task.sh` so that:

1. default behavior uses lean context mode
2. lean context includes only:
   - `03_master_prompt.md`
   - `00_story.md`
   - `02_file_scope.md`
   - optionally `01_context_bundle.md` only if your design clearly justifies it, but prefer not to include it by default
3. a full-context mode is available via explicit CLI flag
4. the runner logs and saves which context files were included in the generated story context
5. existing artifact generation and Codex execution behavior remain intact

## NON-GOALS
Do not:
- change bundle structure
- modify runtime Zumbot code
- modify `automation/scripts/new_story_bundle.sh`
- modify `automation/scripts/run_story.sh`
- modify `automation/scripts/review_story_run.sh`
- add AI review automation
- introduce unrelated refactors

## SOURCE OF TRUTH
- docs/90_codex/CODEX_OPERATING_SYSTEM.md
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md
- docs/90_codex/STORY_BUNDLE_SPEC.md
- automation/run_codex_task.sh
- automation/bundles/active/US-AUTO-4/00_story.md
- automation/bundles/active/US-AUTO-4/01_context_bundle.md
- automation/bundles/active/US-AUTO-4/02_file_scope.md

## FILES ALLOWED TO CHANGE
- automation/run_codex_task.sh
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md

## FILES NOT ALLOWED TO CHANGE
- automation/templates/**
- automation/scripts/new_story_bundle.sh
- automation/scripts/run_story.sh
- automation/scripts/review_story_run.sh
- backend/**
- frontend/**
- .github/**
- deployment / infrastructure files
- database migrations

## BEFORE IMPLEMENTING
1. identify exact files to change
2. explain how lean mode will be selected by default
3. explain how full-context mode will be requested explicitly
4. explain how selected context files will be recorded in run artifacts

## IMPLEMENTATION RULES
- minimal patch only
- no unrelated refactor
- no formatting-only edits
- preserve existing run behavior outside context selection
- prefer simple, readable CLI parsing
- keep full-context mode explicit
- ensure selected context files are traceable in artifacts

## TEST PLAN
At minimum:
- validate shell syntax
- test default lean mode
- test explicit full-context mode
- verify context-file selection is recorded in run artifacts

## OUTPUT FORMAT
Return:
1. changed files summary
2. design rationale
3. validation performed
4. example commands
5. risks / follow-ups
6. final diff
