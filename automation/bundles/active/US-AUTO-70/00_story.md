## Story ID and Title
US-AUTO-70 — Rerun-preflight stable-review recomputation for companion-filtered stories

## Objective
Make `run_story.sh` recompute the effective review surface used by rerun-preflight after companion-artifact filtering has already narrowed the committed implementation surface for a code-only story.

The story must close the specific split confirmed after US-AUTO-69: rerun-preflight must not continue evaluating the unadjusted review surface when companion-artifact filtering has already changed which files are meant to count for acceptance.

## Scope
This story is limited to rerun-preflight and its committed test coverage.

Allowed implementation surface:
- `automation/scripts/run_story.sh`
- `tests/test_run_story.py`

The implementation may:
- recompute or refresh the effective filtered review surface before rerun-preflight decisions are made
- preserve fail-closed behavior if the filtered surface cannot be derived deterministically
- add or update narrowly-scoped tests that prove rerun-preflight uses the recomputed filtered surface

## Non-goals
- Do not modify companion-artifact filtering logic in `automation/run_codex_task.sh`
- Do not modify execution-surface filtering tests in `tests/test_run_codex_task.py`
- Do not change review-stage scripts, gate scripts, or analyze scripts
- Do not broaden this story into reuse, cache, telemetry, UX, or general verification optimization
- Do not redefine allowed scope rules for unrelated stories
- Do not introduce fail-open fallback behavior

## Dependencies
- US-AUTO-57 — blocked line that exposed the original companion-artifact problem
- US-AUTO-69 — split execution-filtering half already landed and must remain untouched here
- Existing committed-HEAD, rerun-boundary, and manual-finish invariants from US-AUTO-46, US-AUTO-47, US-AUTO-52, US-AUTO-53, US-AUTO-54, US-AUTO-55, and US-AUTO-56

## Source of Truth
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/scripts/run_story.sh`
- `tests/test_run_story.py`
- Committed workflow invariants already established in the stable layer of the registry
- The split-story observation recorded for US-AUTO-69 / US-AUTO-70 in the registry

## Current Code Reality
US-AUTO-69 solved only the execution-filtering half by narrowing the committed implementation surface for code-only stories where companion artifacts appeared.

The remaining defect is in `run_story.sh`: rerun-preflight still reasons about the pre-filter or otherwise unadjusted surface, so acceptance can still fail even when the execution surface has already been companion-filtered.

That means the current workflow can still report a rerun-preflight outcome against evidence that is wider than the intended effective review surface for the story.

## Target Outcome
After this story:
- rerun-preflight in `run_story.sh` derives the same effective filtered review surface needed for the current story before it decides whether a rerun is necessary or whether the story remains blocked
- if that filtered surface cannot be derived deterministically, the script must fail closed with a clear blocking error instead of silently using stale or widened evidence
- `tests/test_run_story.py` contains committed coverage proving the recomputation is used for the rerun-preflight decision path
- US-AUTO-70 remains atomic: only rerun-preflight recomputation is addressed here

## Atomic Task Isolation Contract
This story exists because US-AUTO-69 was confirmed to be non-atomic when it combined:
1. companion-artifact execution filtering
2. rerun-preflight stable-review recomputation

This story isolates only item 2.

Hard isolation rules:
- edit only the two allowed files
- do not re-open execution filtering logic
- do not add generic review-surface reuse architecture
- do not fix unrelated rerun or review UX issues opportunistically
- if the recomputation path cannot be implemented within the narrow boundary above, fail closed and stop rather than widening scope

## Risks
- Regressing existing rerun-preflight behavior for stories that do not use companion filtering
- Accidentally coupling `run_story.sh` to execution-stage details that belong exclusively in `run_codex_task.sh`
- Introducing hidden scope drift by changing other pipeline stages indirectly
- Overfitting tests to one scenario without preserving general fail-closed invariants

## Manual Actions
- Update the registry entry for US-AUTO-70 to reflect active bundle work before execution
- Materialize and validate this bundle before running the story
- Commit bundle artifacts before `run_story.sh`
- After implementation commit, rerun from committed HEAD and analyze the fresh run before any review-stage continuation

## Acceptance Notes
Acceptance requires all of the following:
- only `automation/scripts/run_story.sh` and `tests/test_run_story.py` change
- rerun-preflight uses a recomputed effective filtered review surface for the companion-filtered path
- non-companion-filtered paths remain stable
- failures remain fail-closed
- no edits are made to `automation/run_codex_task.sh` or `tests/test_run_codex_task.py`
- the story remains atomic and does not absorb broader safe-reuse or UX work

