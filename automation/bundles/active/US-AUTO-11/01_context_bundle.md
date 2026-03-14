# US-AUTO-11: Context Bundle

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/40_ai/zumbot_codex/REPOSITORY_MAP.md`
- `docs/40_ai/zumbot_codex/PROJECT_CONTEXT.md`
- `automation/run_codex_task.sh`
- `tests/test_run_codex_task.py`

## Current Code Reality
- `automation/run_codex_task.sh` already creates run artifacts, including manifest, story context, diff, pytest output, and review bundle.
- The runner logs context mode and included bundle files.
- The repository already has curated AI-facing repository docs under `docs/40_ai/zumbot_codex/`.

## Architectural Intent
- Add a lightweight repository-map injection step before Codex execution.
- Keep this as a runner concern, not a product-runtime concern.
- Preserve existing workflow and artifact model.
- Prefer a deterministic text artifact over implicit prompt assumptions.

## Minimal Design
- Generate `repository_map_runtime.md` inside the run directory.
- Seed it from stable curated docs and lightweight repo structure summary.
- Reference it from `story_context.md`.
- Record injection status in `manifest.md`.

## Risks
- Overengineering the repository map generator.
- Making the story depend on fragile filesystem introspection.
- Mixing repository-map logic with later stories like allowed-files guard.

## Acceptance Notes
- A run should clearly show whether repository map injection happened.
- The map artifact should exist even before Codex changes anything.
- Tests should verify artifact generation and manifest presence.
