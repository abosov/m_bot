## Story ID and Title
US-AUTO-56 — Post-run stage-gate guidance for review eligibility and manual-finish continuation

## Objective
Add explicit, deterministic operator guidance immediately after post-run decision points so the workflow states whether review-stage commands are allowed, whether commit/discard is required first, and whether manual-finish continuation forbids another rerun.

## Scope
This story is limited to stage-gate guidance and operator messaging around the existing fail-closed workflow contract after `run_story.sh` and `analyze_story_run.sh`.

In scope:
- surface explicit review-eligibility guidance after run/analyze outcomes
- surface explicit commit/discard requirement when the working tree is dirty
- surface explicit rerun prohibition when manual-finish continuation is active
- keep guidance deterministic and aligned with existing workflow invariants
- add targeted tests for the new guidance text and decision framing

## Non-goals
- no new rerun-skip logic
- no new escalation threshold logic
- no new review-artifact reuse logic
- no new telemetry registry or analytics
- no changes to review, classify, or gate decision semantics
- no fail-open fallback behavior
- no broad UX rewrite of all scripts

## Dependencies
- US-AUTO-41 — canonical story-artifact handoff before run
- US-AUTO-44 — dirty-state preflight classification
- US-AUTO-46 — committed-HEAD review boundary enforcement
- US-AUTO-47 — rerun convergence boundary
- US-AUTO-52 — strict manual-finish continuation contract
- US-AUTO-55 — final-HEAD manual-finish review compliance for exact allowed continuation path

## Source of Truth
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/scripts/run_story.sh`
- `automation/scripts/analyze_story_run.sh`
- `tests/test_run_story.py`
- `tests/test_analyze_story_run.py`

## Current Code Reality
The fail-closed workflow contracts already exist, but operator guidance is still too implicit. The registry identifies the next active gap as operator-facing stage guidance after US-AUTO-55. Current behavior can block or redirect correctly, yet operators may still infer the wrong next command from partial output, especially around:
- when review-stage commands are actually allowed
- when dirty-tree state means commit/discard must happen before review
- when manual-finish continuation is active and rerun is forbidden

The pipeline correctness boundary is already implemented; the missing layer is explicit stage-aware guidance.

## Target Outcome
After `run_story.sh` and `analyze_story_run.sh`, the operator should receive deterministic stage-gate guidance that clearly answers:
- Is review-stage allowed now?
- Must the operator commit/discard first?
- Is rerun forbidden because manual-finish continuation is active?
- What is the cheapest safe next step?

This must remain fail-closed and must not relax any existing execution or review boundary.

## Atomic Task Isolation Contract
This story solves exactly one problem: stage-gate guidance after post-run decision points.

Hard isolation rules:
- do not introduce new workflow stages
- do not change review/gate eligibility semantics beyond messaging/explicit surfacing of existing rules
- do not add telemetry, caching, reuse, retry, or loop-control logic
- do not expand into bundle-pack workflow simplification
- do not modify unrelated scripts or tests outside the listed scope

If a change requires new enforcement behavior rather than explicit guidance of existing behavior, stop and leave it for a follow-up story.

## Risks
- wording drift could accidentally change operator interpretation of existing contracts
- tests may overfit exact strings instead of stable stage-gate meaning
- scope drift into rerun-control or review-boundary logic is a real risk and must be rejected

## Manual Actions
- update the registry row for US-AUTO-56 from `Planned` to `Bundle Ready` when the bundle is committed
- keep US-AUTO-57 as the next recommended implementation follow-up after US-AUTO-56
- after implementation, verify guidance output on both normal rerun path and manual-finish continuation path

## Acceptance Notes
Acceptance requires all of the following:
- `run_story.sh` or `analyze_story_run.sh` emits explicit stage-gate guidance for normal post-run outcomes
- dirty-tree states explicitly tell the operator that review-stage is not allowed until commit/discard resolves the tree
- manual-finish continuation explicitly tells the operator not to rerun again until manual finish is completed
- guidance is deterministic, fail-closed, and consistent with existing committed-HEAD / manual-finish contracts
- tests prove the guidance exists for the intended paths without broadening scope

