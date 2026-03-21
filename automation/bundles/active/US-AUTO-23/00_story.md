# US-AUTO-23: Story Change Ledger

## Story ID and Title
- Story ID: `US-AUTO-23`
- Title: `Story Change Ledger`

## Objective
Add a durable append-only story ledger that records normalized story lifecycle events across run, review, reject/follow-up, and finalize/close checkpoints so later anti-cycle stories can consume committed evidence instead of reconstructing history from scattered artifacts.

## Scope
- Add one repository-visible ledger artifact under `automation/`.
- Add one small helper/writer for appending normalized ledger entries.
- Record ledger entries at a minimal set of stable lifecycle checkpoints:
  - story start
  - review outcome
  - finalize/close outcome
- Add focused tests for append behavior and lifecycle recording.
- Update shared docs/checklists only as needed to describe the ledger as an evidence layer.
- Update epic registry status/details only as needed for this story.

## Non-goals
- Do not implement loop detection preflight.
- Do not block story execution based on ledger history.
- Do not add expensive rerun budget logic.
- Do not add pipeline zone caps.
- Do not add escalation gates.
- Do not redesign merge recommendation or review classification semantics.
- Do not introduce operator dashboarding or broad UX changes.
- Do not add database-backed persistence or external telemetry.

## Dependencies
- Existing story execution lifecycle already provides stable start, review, and finalize/close phases.
- Epic anti-cycle roadmap expects `US-AUTO-23` to provide the evidence primitive for downstream stories such as `US-AUTO-24` through `US-AUTO-27`.
- Shared bundle validation structure in `docs/90_codex/STORY_BUNDLE_SPEC.md` must be followed exactly.

## Source of Truth
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- existing automation lifecycle scripts that already define canonical run/review/finalize flow

## Current Code Reality
- Story run artifacts and review outputs exist, but there is no single durable committed ledger that normalizes story-level lifecycle history.
- Anti-cycle work is planned in the registry, but the shared evidence primitive for repeated-iteration analysis does not yet exist.
- The workflow already values narrow scope, deterministic stages, and explicit follow-up capture instead of mixing multiple enforcement layers into one story.

## Target Outcome
After this story:
- the repository contains one canonical append-only story ledger artifact
- lifecycle scripts append normalized entries at a small number of stable checkpoints
- reviewers can inspect story attempt history in one place
- downstream anti-cycle stories can read the ledger rather than reconstructing history from multiple ad hoc artifacts