# US-AUTO-20 PROMPT 1 — Workflow Chaining & Resume

## Role
You are the Zumbot workflow automation engineer working under the repository's CODEX Operating System.

## Goal
Add a deterministic operator workflow helper that reports the latest valid stage of a story run, recommends the exact next command, and supports safe resume from existing run artifacts.

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/run_codex_task.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh
## Files Allowed To Change
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/**`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `tests/**`
- `automation/bundle_packs/**`
- `automation/bundles/active/US-AUTO-20/**`

## Files Not Allowed To Change
- `backend/**`
- `migrations/**`
- `web/**`
- `admin_api.py`
- `database.py`
- product application flows unrelated to automation
- autonomous/background execution infrastructure

## Atomic Task Isolation Contract
- Intent statement: implement only chaining/resume guidance for the existing automation workflow.
- Out of scope: backend changes, broad UX redesign, autonomous execution, unrelated cleanup.
- Atomic Task Isolation is mandatory for this run.
- Before changing files, declare the one-sentence task intent.
- If the task becomes non-atomic, underspecified, or split across multiple independent findings, stop.
- Capture newly discovered out-of-scope findings as follow-up work instead of expanding this run.
- Follow-up prompts are not an exception path around Atomic Task Isolation.

## Output
Return:
1. changed files summary
2. stage model summary
3. validation performed
4. risks / follow-ups
5. final diff

