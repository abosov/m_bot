# US-AUTO-11: Repository Map Injection for Codex runs

## Story ID and Title
- Story ID: `US-AUTO-11`
- Title: `Repository Map Injection for Codex runs`

## Objective
Inject a durable repository map artifact into every Codex run so the model receives a stable architectural view of the Zumbot repository before implementation starts.

## Scope
- Extend `automation/run_codex_task.sh` to generate a runtime repository map artifact before Codex execution.
- Include the repository map in run artifacts and make its presence explicit in the run manifest.
- Ensure Codex-facing run context references the repository map artifact.
- Add focused tests for repository map generation/injection behavior.
- Update workflow docs/checklists for the new invariant.

## Non-goals
- Do not implement allowed-files enforcement.
- Do not implement AI review gate classification changes.
- Do not redesign the whole automation system.
- Do not change product runtime code.
- Do not introduce a large repo analysis framework.

## Dependencies
- Existing story bundle workflow.
- Existing isolated worktree execution.
- Existing materialization and artifact collection flow.

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/40_ai/zumbot_codex/REPOSITORY_MAP.md`
- `docs/40_ai/zumbot_codex/PROJECT_CONTEXT.md`
- `automation/run_codex_task.sh`
- `tests/test_run_codex_task.py`

## Current Code Reality
- The runner already generates `story_context.md`, `manifest.md`, and review artifacts.
- The repository contains a curated AI-facing repository map document, but the runner does not inject a dedicated repository-map artifact into each run.
- Codex execution currently depends mostly on bundle context and prompt content, which is not enough for durable architecture awareness.

## Target Outcome
Each Codex run must contain:
- `repository_map_runtime.md`
- explicit manifest evidence that repository map injection happened
- Codex-facing context that references the injected map artifact
