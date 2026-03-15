# US-AUTO-16 PROMPT 1 — AI Review Gate

## Role
You are the System Architect + Data Architect + UX + Developer + Tech Writer + QA + Security Reviewer for Zumbot.

## Task
Implement a narrow AI review gate orchestration flow for story runs. Reuse the existing AI review and review classification scripts, add a single orchestration entrypoint, and produce a machine-readable final gate result artifact with an explicit `approve` or `reject` decision.

## Mandatory Context
Read and follow:
- docs/90_codex/CODEX_OPERATING_SYSTEM.md
- docs/90_codex/PROJECT_CONTEXT.md
- docs/90_codex/REPOSITORY_MAP.md
- docs/90_codex/PROJECT_CONTEXT_UPDATE_PROTOCOL.md
- docs/90_codex/REVIEW_CLASSIFICATION_RULES.md
- automation/bundles/active/US-AUTO-16/00_story.md
- automation/bundles/active/US-AUTO-16/01_context_bundle.md
- automation/bundles/active/US-AUTO-16/02_file_scope.md

## Goal
Create a stable review gate layer that can be called for a story ID and the latest run, writes a final gate result artifact, and exits non-zero if the gate rejects merge or cannot derive a valid decision.

## Non-goals
Do not:
- modify `automation/scripts/finalize_story.sh`
- integrate gate checks into merge/finalize flow
- redesign the LLM review/classification process
- change unrelated automation runner behavior
- add unrelated refactors or formatting-only edits

## Source of Truth
- `docs/90_codex/REVIEW_CLASSIFICATION_RULES.md`
- `automation/bundles/active/US-AUTO-16/00_story.md`
- `automation/bundles/active/US-AUTO-16/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-16/02_file_scope.md`

## Files Allowed To Change
- `tests/test_run_codex_task.py`
- `tests/test_review_classification_script.py`
- `tests/test_review_gate_story_run.py`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/templates/review_prompt_template.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `automation/run_codex_task.sh`

## Files Not Allowed To Change
- `automation/scripts/finalize_story.sh`
- `automation/scripts/check_allowed_files.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `backend/**`
- `database/**`

## Implementation Rules
- minimal patch only
- no unrelated refactor
- no formatting-only edits
- update docs only when behavior/process changes require it

## Test Plan
- `pytest tests/test_review_classification_script.py tests/test_review_story_run.py tests/test_review_gate_story_run.py tests/test_run_codex_task.py`

## Output
Return:
1. changed files summary
2. rationale
3. test results
4. risks/follow-ups
5. final diff

