# US-AUTO-7 PROMPT 1 — Stable review evidence from commit range

## ROLE
You are the System Architect + Data Architect + UX + Developer + Tech Writer + QA + Security Reviewer for Zumbot.

## TASK
<Atomic implementation task for this prompt>

## MANDATORY CONTEXT
Read and follow:
- docs/90_codex/CODEX_OPERATING_SYSTEM.md
- docs/90_codex/PROJECT_CONTEXT.md
- docs/90_codex/REPOSITORY_MAP.md
- docs/90_codex/PROJECT_CONTEXT_UPDATE_PROTOCOL.md
- <story-specific architecture/product docs>
- automation/bundles/active/US-AUTO-7/00_story.md
- automation/bundles/active/US-AUTO-7/01_context_bundle.md
- automation/bundles/active/US-AUTO-7/02_file_scope.md

## GOAL
<Expected end state for this prompt>

## NON-GOALS
Do not:
- <explicit forbidden action>
- <explicit forbidden action>

## SOURCE OF TRUTH
- <primary architecture/product source>

## FILES ALLOWED TO CHANGE
- <allowed file path>
- <allowed file path>

## FILES NOT ALLOWED TO CHANGE
- <forbidden file path>
- <forbidden area>

## IMPLEMENTATION RULES
- minimal patch only
- no unrelated refactor
- no formatting-only edits
- update docs only when behavior/process changes require it

## TEST PLAN
- `pytest <targeted test path>`

## OUTPUT FORMAT
Return:
1. changed files summary
2. rationale
3. test results
4. risks/follow-ups
5. final diff
