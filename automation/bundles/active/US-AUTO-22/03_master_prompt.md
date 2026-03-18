# US-AUTO-22 PROMPT 1 — Atomic task isolation rule for Codex workflow

## Role
You are the System Architect + Data Architect + UX + Developer + Tech Writer + QA + Security Reviewer for Zumbot.

## Task
Update Codex workflow documentation and prompt templates so Atomic Task Isolation becomes an explicit mandatory contract for story execution and follow-up execution.

## Task Intent
Declare this exact sentence before making changes: `Introduce Atomic Task Isolation as an explicit mandatory contract in Codex workflow docs and prompt templates for this story.`

## Atomic Task Isolation Contract
- This run has one purpose only: make Atomic Task Isolation explicit and mandatory in Codex workflow docs and prompt templates for this story.
- Atomic Task Isolation is a mandatory execution contract for this run, not optional guidance.
- If the required intent, out-of-scope, file-boundary, follow-up-capture, or hard-stop fields are missing or ambiguous, stop and refuse implementation until the prompt is corrected.
- If another independently reviewable documentation or process change is discovered, do not absorb it into this run; record it as a separate follow-up.

## Mandatory Context
Read and follow:
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/40_ai/zumbot_codex/MASTER_PROMPT_TEMPLATE.md`
- `docs/40_ai/zumbot_codex/FOLLOWUP_PROMPT_TEMPLATE.md`
- `automation/bundles/active/US-AUTO-22/00_story.md`
- `automation/bundles/active/US-AUTO-22/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-22/02_file_scope.md`

## Goal
Make Atomic Task Isolation explicit in the source-of-truth docs and prompt templates without changing runtime scripts or test infrastructure.

## Non-goals
Do not:
- modify any automation shell scripts
- change allowed-files guard behavior
- change review gate behavior
- add runtime enforcement
- refactor unrelated documentation

## Source of Truth
- `automation/bundles/active/US-AUTO-22/00_story.md`
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`

## Files Allowed To Change
- `automation/bundle_packs/US-AUTO-22.bundle.md`
- `automation/bundles/active/US-AUTO-22/00_story.md`
- `automation/bundles/active/US-AUTO-22/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-22/02_file_scope.md`
- `automation/bundles/active/US-AUTO-22/03_master_prompt.md`
- `automation/bundles/active/US-AUTO-22/04_review_checklist.md`
- `automation/bundles/active/US-AUTO-22/05_followups.md`
- `automation/bundles/active/US-AUTO-22/06_manual_actions.md`
- `docs/40_ai/zumbot_codex/MASTER_PROMPT_TEMPLATE.md`
- `docs/40_ai/zumbot_codex/FOLLOWUP_PROMPT_TEMPLATE.md`
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`

## Files Not Allowed To Change
- `automation/scripts/**`
- `automation/run_codex_task.sh`
- `tests/**`
- `backend/**`

## Implementation Rules
- minimal patch only
- no unrelated refactor
- no formatting-only edits
- update docs only when behavior/process changes require it
- keep this story documentation/prompt-template only
- keep the executable prompt allowlist aligned with the legitimate story implementation surface so bundle artifacts used by this story are not under-declared
- if shell enforcement is needed, record it as a follow-up story instead of implementing it here
- explicitly declare task intent in one sentence before making changes
- do not expand scope beyond declared intent
- if out-of-scope issue is discovered, record it as follow-up instead of fixing it
- if task cannot be completed within allowed scope, stop and require a new story
- if another independently reviewable documentation/process change is discovered, do not absorb it into this run; record it as a separate follow-up

## Test Plan
- Validate that the story bundle materializes without unresolved placeholders.
- Review changed documentation for explicit Atomic Task Isolation language.
- No pytest changes required for this documentation-only story.

## Output
Return:
1. changed files summary
2. rationale
3. validation results
4. risks/follow-ups
5. final diff

