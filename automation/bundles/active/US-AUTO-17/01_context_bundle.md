# US-AUTO-17: Context Bundle

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/40_ai/zumbot_codex/REPOSITORY_MAP.md`
- `docs/40_ai/zumbot_codex/PROJECT_CONTEXT.md`
- `automation/run_codex_task.sh`
- `tests/test_run_codex_task.py`

## Current Code Reality
- The runner already generates a runtime repository map artifact.
- The current implementation is intentionally lightweight and deterministic, based on curated docs plus top-level repository directories.
- The runner already knows the active `STORY_ID` and bundle directory, so story-local repository-map enrichment can be added without changing the overall run model.
- Story bundles already encode allowed-file scope, which can be surfaced to Codex as architecture context without changing enforcement logic.

## Architectural Intent
- Keep `automation/run_codex_task.sh` as the single owner of repository-map runtime generation.
- Enrich the map with higher-signal architecture guidance instead of building a complex repository crawler.
- Reuse bundle scope as context, not as a second enforcement mechanism.
- Make Codex more architecture-aware before implementation starts, while preserving deterministic runner artifacts.

## Risks
- Overbuilding the repository-map artifact into a mini-framework instead of a compact runtime aid.
- Duplicating allowed-files enforcement logic instead of only surfacing story-local context.
- Making parsing of `02_file_scope.md` brittle if the implementation depends on overly narrow formatting assumptions.
- Mixing future console-UX/chaining concerns into this story.

## Acceptance Notes
- `repository_map_runtime.md` must become visibly richer than the baseline version.
- Layer boundaries must be explicit and repository-valid.
- Story-local context must reflect the active story bundle.
- Anti-hallucination rules must be clearly visible to Codex.
- Dependency hints must describe the runner/review/classification/gate relationship without changing gate logic.

