
US-AUTO-16: Follow-Ups
## Follow-Up Prompt Queue

Integrate AI review gate into finalize_story.sh as a blocking pre-merge condition.

Add dedicated automated tests for review gate parsing and decision handling.

## Iteration Notes

Keep this story limited to creating the gate orchestration and result artifact contract.

Defer finalize integration to the next automation story.

Prefer explicit fail-closed behavior if classification output is ambiguous.

Follow-Up Prompt Template

# US-AUTO-16 FOLLOW-UP PROMPT 1 — <Fix/Adjustment>

## Role
You are the System Architect + Developer + QA + Security Reviewer for Zumbot.

## Context
- Base story bundle: `automation/bundles/active/US-AUTO-16/`
- Previous run output: `automation/output/<story-run-id>/`
- Review checklist: `automation/bundles/active/US-AUTO-16/04_review_checklist.md`

## Target
Fix only the specific review gate issue identified during review without expanding scope into finalize integration or unrelated automation refactors.

## Findings To Address
- <finding>
- <finding>

## Files Allowed To Change
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_sty_run.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/templates/review_prompt_template.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`

## Files Not Allowed To Change
- `automation/scripts/finalize_story.sh`
- `automation/run_codex_task.sh`
- `backend/**`
- `database/**`
- `tests/**`

## Rules
- keep patch minimal and scoped
- preserve architecture boundaries
- do not introduce new features beyond listed findings

## Tests
- `pytest tests/test_allowed_files_guard.py`

## Output
Return:
1. addressed findings
2. changed files summary
3. test results
4. residual risks
5. final diff

PR Description Template

# US-AUTO-16 — AI Review Gate

## Summary
- add a single AI review gate orchestration script
- reuse existing AI review and classification steps
- write a machine-readable gate result artifact with explicit approve/reject status

## Story Context
- Story bundle: `automation/bundles/active/US-AUTO-16/`
- Objective: create a stable gate result r downstream automation
- Non-goals: no finalize integration, no merge-policy changes, no unrelated refactor

## Scope
- review gate orchestration for latest story run
- stable gate result artifact contract
- minimal docs/process update if needed

## Files Changed
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_story_run.sh`
- `automation/templates/review_prompt_template.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`


