# US-AUTO-17: Repository Map Injection v2

## Story ID and Title
- Story ID: `US-AUTO-17`
- Title: `Repository Map Injection v2`

## Objective
Strengthen Codex anti-hallucination context by upgrading the runtime repository map from a generic top-level overview into a story-aware architecture artifact with explicit layer boundaries, story-local file guidance, anti-hallucination rules, and dependency hints.

## Scope
- Extend `automation/run_codex_task.sh` so `repository_map_runtime.md` contains:
  - explicit architecture layer boundaries
  - a story-local context section for the active story
  - anti-hallucination rules for Codex
  - dependency hints for the automation pipeline
- Reuse existing bundle scope data from `automation/bundles/active/<STORY-ID>/02_file_scope.md` when building story-local repository context.
- Ensure generated `story_context.md` and `codex_prompt.md` continue to reference the runtime repository map artifact.
- Update focused tests for repository map generation and injection behavior.
- Update workflow documentation/checklists so Repository Map Injection v2 becomes part of the expected runner behavior.

## Non-goals
- Do not implement allowed-files enforcement changes in this story.
- Do not implement console UX improvements, chaining, resume, or long-wait logging in this story.
- Do not redesign AI review / classification / review gate.
- Do not change backend product runtime code.
- Do not introduce a heavy repository indexing system or non-deterministic scanning layer.

## Dependencies
- Existing bundle-pack + materialization workflow.
- Existing isolated worktree execution.
- Existing repository map injection baseline from `US-AUTO-11`.
- Existing story file-scope contract in active bundles.

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/40_ai/zumbot_codex/REPOSITORY_MAP.md`
- `docs/40_ai/zumbot_codex/PROJECT_CONTEXT.md`
- `automation/run_codex_task.sh`
- `automation/scripts/run_story.sh`
- `automation/scripts/validate_story_bundle.sh`
- `tests/test_run_codex_task.py`

## Current Code Reality
- `automation/run_codex_task.sh` already generates `repository_map_runtime.md`, injects it into `codex_prompt.md`, and records repository-map metadata in the run manifest.
- The current repository map is useful but still too generic: it lists top-level directories and curated docs, but it does not clearly separate architecture layers, story-local allowed/forbidden paths, anti-hallucination rules, or pipeline dependency hints.
- Active story bundles already contain explicit file-scope data in `02_file_scope.md`, but the runner does not reuse that information inside the runtime repository map.
- Tests already cover baseline repository-map generation/injection behavior and should be extended rather than replaced.

## Target Outcome
Each Codex run must produce a stronger `repository_map_runtime.md` that includes:
- architecture layer boundaries
- story-local context derived from the active story bundle
- anti-hallucination rules for Codex
- dependency hints describing how pipeline artifacts relate to each other

The result must stay deterministic, lightweight, and runner-owned.

