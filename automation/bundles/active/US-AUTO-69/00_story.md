## Story ID and Title
US-AUTO-69 — Companion-artifact execution filtering for code-only stories

## Objective
Allow a code-only story run to complete when Codex emits companion registry or documentation edits that are outside the intended implementation scope, but only by filtering those companion artifacts out of the execution review surface rather than widening the story scope.

## Scope
This story is limited to the execution-layer handling of companion artifacts for code-only stories.
It may:
- detect companion-artifact paths produced during Codex execution
- exclude those paths from the effective implementation review surface used by the execution flow
- preserve fail-closed behavior when non-companion out-of-scope changes remain
- add targeted tests for the new execution behavior

This story must not redesign the broader scope-validation model, the registry workflow, or review-stage semantics.

## Non-goals
- Do not make documentation or registry files generally allowed for code-only stories
- Do not change story bundle validation rules
- Do not alter manual-finish continuation logic
- Do not introduce fail-open scope handling
- Do not add telemetry, operator UX redesign, or reuse logic
- Do not mutate the durable registry automatically as part of runtime filtering

## Dependencies
- US-AUTO-41 — story-artifact commit handoff before run
- US-AUTO-44 — materialization preflight and operator handoff
- US-AUTO-46 — committed-HEAD review boundary enforcement
- US-AUTO-49 — runtime scope validation ignores committed active-story bundle artifacts
- US-AUTO-50 — deterministic structured AI review output contract
- US-AUTO-56 — post-run stage-gate guidance
- US-AUTO-57 — blocked predecessor whose execution blocker is being isolated by this follow-up :contentReference[oaicite:0]{index=0}

## Source of Truth
Primary source of truth for prioritization, dependency context, and current status:
- `docs/90_codex/epics/US-AUTO_REGISTRY.md` :contentReference[oaicite:1]{index=1}

Implementation source of truth for this story:
- runtime execution path in `automation/scripts/run_story.sh`
- Codex execution output shaping in `automation/run_codex_task.sh`
- related focused tests in `tests/test_run_story.py` and `tests/test_run_codex_task.py`

## Current Code Reality
The registry records US-AUTO-57 as blocked even though implementation and tests were completed, because Codex execution added a companion edit to `docs/90_codex/epics/US-AUTO_REGISTRY.md`, which fell outside the code-only story scope and caused the run to fail during scope validation. The registry explicitly identifies this as an execution-layer blocker and points to US-AUTO-69 as the narrow follow-up to resolve it. :contentReference[oaicite:2]{index=2}

The current workflow already distinguishes committed story artifacts from implementation delta, enforces committed-HEAD boundaries, and prefers fail-closed behavior. The missing piece is a narrow execution-layer rule that recognizes a small class of companion artifacts for code-only stories and removes them from the effective review surface without silently allowing arbitrary extra edits. :contentReference[oaicite:3]{index=3}

## Target Outcome
After this story:
- a code-only story run no longer fails solely because Codex also emitted a recognized companion registry or documentation edit
- those companion paths are excluded from the effective execution review surface
- the workflow still hard-fails when any remaining out-of-scope non-companion file is present
- the result is deterministic and review-surface fidelity is preserved for the actual code change set
- US-AUTO-57’s execution blocker becomes removable without weakening the pipeline’s fail-closed posture

## Atomic Task Isolation Contract
This story is atomic.
It solves exactly one problem: execution-layer filtering of recognized companion artifacts for code-only stories.

Allowed change categories:
- companion-artifact path classification logic
- effective changed-files filtering for execution review surface
- deterministic error/allow behavior for companion vs non-companion extra edits
- tightly scoped tests

Forbidden expansions:
- no new workflow phases
- no registry redesign
- no generalized multi-category scope policy engine
- no review-stage or analyze-stage redesign
- no documentation automation logic

If implementation pressure suggests broader policy changes, stop and reject rather than expanding scope.

## Risks
- Risk of accidental fail-open handling if companion filtering is too broad
- Risk of drift between filtered changed-files surface and diff.patch surface
- Risk of masking real out-of-scope edits if path classification is ambiguous
- Risk of regression in existing strict scope-validation behavior for non-companion files

## Manual Actions
- Update the registry entry for US-AUTO-69 from `Planned` to `Bundle Drafted` when the bundle is materialized and committed
- Keep US-AUTO-57 as `Blocked` until US-AUTO-69 is implemented, rerun, reviewed, and merged
- After implementation, reassess whether US-AUTO-57 should move from blocked to resumed or implemented based on committed evidence
- Use the standard bundle-first workflow described in `06_manual_actions.md`

## Acceptance Notes
Acceptance requires all of the following:
- code-only execution treats recognized companion artifact paths as filtered, not as allowed implementation scope
- at least one focused test proves that a recognized companion registry/doc path does not fail the run by itself
- at least one focused test proves that a non-companion out-of-scope path still hard-fails
- if both a recognized companion path and a real out-of-scope path appear together, the run still hard-fails
- effective changed-files and any related execution diff surface remain consistent with the filtering rule
- no unrelated files or stages are changed

