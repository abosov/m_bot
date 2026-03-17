# US-AUTO-19 PROMPT 1 — Failure Surfacing & Artifact Summaries

## Role
You are the Zumbot workflow automation engineer working under the repository's CODEX Operating System.

## Goal
Implement a read-only operor analysis command that summarizes story run artifacts and failure state from `automation/runs/<STORY_ID>/<RUN_ID>/`.

## Source of Truth
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`

## Files Allowed To Change
- `automation/scripts/analyze_story_run.sh`
- `tests/test_analyze_story_run.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `automation/bundle_packs/US-AUTO-19.bundle.md`
- `automation/bundles/active/US-AUTO-19/**`

## Files Not Allowed To Change
- `automation/run_codex_task.sh`
- `automation/scripts/run_story.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/finalize_story.sh`
- `backend/**`
- `frontend/**`
- `migrations/**`
- `.github/**`

## Requirements
1. Add `automation/scripts/analyze_story_run.sh`.
2. The script must accept:
   - positional story id
   - optional `AUTOMATION_RUN_DIR` override
3. By default it must inspect the latest run directory under:
   - `automation/runs/<STORY_ID>/`
4. It must be read-only.
5. It must tolerate missing files and incomplete runs.
6. It must print a compact, operator-friendly summary.
7. It must summarize, when available:
   - manifest metadata
   - changed files count or preview
   - pytest outcome
   - AI review artifact presence
   - classification recommendation
   - gate decision
8. It must produce a final status line that helps the operator decide the next action quickly.
9. Add focused tests using synthetic run directories.
10. Update workflow docs to mention the analysis command.

## Suggested Output Shape
A compact structure like:

- Story / Run / Directory
- Artifact Presence
- Branch / Starting HEAD / Review Base
- Changed Files
- Pytest
- Review Pipeline
- RUN STATUS

The exact wording may differ, but the output should remain stable and concise.

## Rules
- Keep the patch minimal and scoped
- No unrelated refactor
- No mutation of existing run artifacts
- Prefer robust small parsing helpers over complex logic
- Do not infer success from missing artifacts
- Fail clearly on invalid story id or missing story run root
- Support deterministic tests

## Test Plan
- `pytest tests/test_analyze_story_run.py`

## Output Format
Return:
1. changed files summary
2. implementation notes
3. test results
4. residual risks / follow-ups
5. final diff

