Story-ID: US-AUTO-19
Version: 1

=== FILE: 00_story.md ===
# US-AUTO-19: Failure Surfacing & Artifact Summaries

## Story ID and Title
- Story ID: `US-AUTO-19`
- Title: `Failure Surfacing & Artifact Summaries`

## Objective
Provide a single read-only operator command that summarizes the latest or selected story run so pipeline failures can be diagnosed without manually opening multiple artifacts under `automation/runs/<STORY_ID>/<RUN_ID>/`.

## Problem
Today, when a story run fails or needs inspection, the operator often has to manually inspect several files such as:
- `manifest.md`
- `run_meta.txt`
- `changed_files.txt`
- `diff.stat`
- `pytest.txt`
- `ai_review_result.md`
- `review_classification.md`
- `review_gate_result.json`

This slows debugging and makes operator experience inconsistent.

## Scope
- Add a new analysis script:
  - `automation/scripts/analyze_story_run.sh`
- The script must:
  - resolve the latest run for a story by default
  - support `AUTOMATION_RUN_DIR` override for inspecting a specific run
  - print a compact human-readable summary to stdout
  - tolerate missing artifacts and incomplete runs
  - remain strictly read-only
- Add focused tests for:
  - latest-run resolution
  - explicit run-dir override
  - missing artifacts
  - failed/incomplete run visibility
- Update workflow documentation to include the new analysis command.

## Non-goals
- No changes to `automation/run_codex_task.sh`
- No changes to execution semantics of `run_story.sh`
- No automatic retry or auto-fix loop
- No changes to AI review, classification, or gate decision logic
- No mutation of run artifacts
- No pipeline orchestration/chaining in this story

## Operator Outcomes
The operator should be able to run:

`automation/scripts/analyze_story_run.sh US-AUTO-17`

and immediately see:
- story id / run id
- run directory
- branch / starting head / review base if available
- artifact presence summary
- changed files summary
- pytest outcome summary
- AI review / classification / gate outcome summary
- a final high-signal “current status” line

## Dependencies
- existing run artifacts under `automation/runs/<STORY_ID>/<RUN_ID>/`
- `manifest.md`
- `run_meta.txt`
- optional review/gate artifacts

## Source of Truth
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`

## Current Code Reality
- Operators currently inspect run artifacts manually under `automation/runs/<STORY_ID>/<RUN_ID>/`.
- There is no single read-only script that summarizes pytest, review, classification, and gate artifacts together.
- Existing scripts generate and consume artifacts, but the operator must open multiple files to understand the current run state.

## Target Outcome
- One read-only command can summarize the latest or selected run for a story.
- Missing or incomplete artifacts are surfaced clearly instead of being mistaken for success.
- Operators can identify likely next actions quickly from one compact summary.

## Implementation Rules
- Keep the script read-only
- Prefer compact shell parsing over heavyweight dependencies
- Missing artifacts must be surfaced clearly, not treated as success
- The command should stay useful for both successful and failed runs
- Output should be concise, stable, and operator-oriented
- No unrelated refactors

## Testing
- `pytest tests/test_analyze_story_run.py`

## Documentation
- Update only docs required by the new operator workflow step

=== FILE: 01_context_bundle.md ===
# US-AUTO-19: Context Bundle

## Source of Truth
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`

## Current Code Reality
- Run artifacts already exist under `automation/runs/<STORY_ID>/<RUN_ID>/`.
- Review, classification, and gate scripts already write their own artifacts.
- There is no single operator command that summarizes run state and artifact availability in one place.
- Debugging often requires manually opening multiple files.

## Architectural Intent
- Add one narrow read-only analysis layer for operator UX.
- Reuse existing artifact formats instead of redesigning them.
- Keep execution flow unchanged and avoid coupling this story to orchestration or retry behavior.

## Risks
- Over-parsing artifact content could make the script brittle.
- Treating missing artifacts as implied success would mislead the operator.
- Scope creep into orchestration, retries, or pipeline mutation must be avoided.

## Acceptance Notes
- The analysis command must remain read-only.
- It must tolerate incomplete runs and missing artifacts.
- It must produce a concise summary with a final operator-facing run status.

=== FILE: 02_file_scope.md ===
# US-AUTO-19: File Scope

## Files Allowed To Change
- `automation/scripts/analyze_story_run.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `automation/bundle_packs/US-AUTO-19.bundle.md`
- `automation/bundles/active/US-AUTO-19/**`
- `tests/test_analyze_story_run.py`

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

## Scope Notes
- Add a new read-only script rather than modifying core execution flow
- Do not redesign artifact formats in this story
- Tests should use synthetic run directories and fixture artifacts

=== FILE: 03_master_prompt.md ===
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

=== FILE: 04_review_checklist.md ===
# US-AUTO-19: Review Checklist

## Scope Validation
- [ ] Changes stay inside `02_file_scope.md`
- [ ] No core pipeline execution semantics were changed
- [ ] No AI review / classification / gate logic was modified
- [ ] No unrelated refactor or formatting-only edits

## Functional Validation
- [ ] `automation/scripts/analyze_story_run.sh` is read-only
- [ ] Latest run resolution works
- [ ] `AUTOMATION_RUN_DIR` override works
- [ ] Missing artifacts are surfaced clearly
- [ ] Incomplete runs still produce useful output
- [ ] Output includes final status line
- [ ] Output remains concise and operator-oriented

## Verification
- [ ] Focused tests added
- [ ] Docs updated for the new operator command
- [ ] Manual command for local use is recorded
- [ ] Risks and follow-ups captured before merge

=== FILE: 05_followups.md ===
# US-AUTO-19: Follow-Ups

## Follow-Up Prompt Queue
- `US-AUTO-20` — Workflow Chaining & Resume
- `US-AUTO-21` — Long-Running Step Logging
- `US-AUTO-22` — Review Result Rendering

## Iteration Notes
- Keep this story narrow: failure surfacing oDo not fold orchestrator behavior into this story
- Do not add auto-fix loop in this story
- If operators later need machine-readable output, add that as a separate follow-up

=== FILE: 06_manual_actions.md ===
# US-AUTO-19: Manual Actions

## Required Human Actions
- Materialize the bundle pack into `automation/bundles/active/US-AUTO-19/`
- Run the new analysis command against at least one existing story run
- Confirm the output is materially faster to inspect than opening artifacts manually

## Execution Notes
- Run locally:
  - `automation/scripts/materialize_story_bundle.sh US-AUTO-19`
  - `automation/scripts/validate_story_bundle.sh US-AUTO-19`
  - implement the story changes
  - `pytest tests/test_analyze_story_run.py`
- Suggested manual checks:
  - `automation/scripts/analyze_story_run.sh US-AUTO-17`
  - `AUTOMATION_RUN_DIR=<specific-run-dir> automation/scripts/analyze_story_run.sh US-AUTO-17`

## Completion Status
- [ ] Manual verification completed
- [ ] Ready for PR
