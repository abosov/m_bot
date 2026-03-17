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

