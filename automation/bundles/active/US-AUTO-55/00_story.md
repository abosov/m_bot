# US-AUTO-55

## Story ID and Title
US-AUTO-55 — Manual-finish final-HEAD review compliance after allowed non-converging rerun continuation

## Objective
Restore strict but usable downstream review compliance for the one allowed exception path introduced by the workflow: manual-finish continuation after `blocked_non_converging_rerun`.

The story must ensure that `ai_review_story_run.sh`, `classify_review_story_run.sh`, `review_gate_story_run.sh`, and `analyze_story_run.sh` treat that allowed continuation path consistently with final reviewed `HEAD` semantics, without reopening rerun loops and without weakening committed-HEAD review boundaries.

## Scope
In scope:
- downstream review-stage compliance for the exact allowed manual-finish continuation path
- final-HEAD evidence handling for pinned run artifacts after branch tip advances through allowed manual finish
- deterministic fail-closed rejection when final-HEAD compliance cannot be proven
- focused regression coverage for the exact allowed path and nearby reject cases
- registry and story artifact updates required by this story

Out of scope:
- diff fidelity changes already completed in US-AUTO-54
- rerun orchestration changes
- retry logic changes
- operator UX messaging improvements beyond minimal evidence/reason surfacing needed for correctness
- broad manual-finish redesign
- escalation logic and unrelated pipeline stages

## Non-goals
- Do not change the normal rule that ordinary review must consume a fresh committed-head rerun.
- Do not make `run -> commit -> review` valid as a general workflow.
- Do not weaken workspace-only, stale-run, or ancestor/descendant boundary checks outside the exact allowed manual-finish continuation contract.
- Do not introduce fallback behavior that silently accepts unproven final-HEAD lineage.
- Do not broaden this story into stage-gate guidance; that remains US-AUTO-56.

## Dependencies
- US-AUTO-46 — committed-HEAD review boundary
- US-AUTO-47 — rerun convergence boundary
- US-AUTO-52 — strict manual-finish continuation contract
- US-AUTO-53 — committed-HEAD diff.patch review fidelity
- US-AUTO-54 — rerun diff fidelity fix for the reproduced US-AUTO-28-F1 path

## Source of Truth
- docs/90_codex/epics/US-AUTO_REGISTRY.md
- automation/scripts/ai_review_story_run.sh
- automation/scripts/classify_review_story_run.sh
- automation/scripts/review_gate_story_run.sh
- automation/scripts/analyze_story_run.sh
- tests/test_ai_review_story_run.py
- tests/test_classify_review_story_run.py
- tests/test_review_gate_story_run.py
- tests/test_analyze_story_run.py
- tests/test_review_pipeline_validation_contract.py

## Current Code Reality
US-AUTO-54 fixed the rerun-artifact diff fidelity defect for the reproduced US-AUTO-28-F1 path, so `review_diff_patch_mismatch` is no longer the blocker on a clean committed-head rerun.

The remaining defect is narrower:
- the pipeline explicitly allows manual-finish continuation after `blocked_non_converging_rerun`
- during that allowed continuation, branch `HEAD` advances
- pinned run artifacts remain tied to the pre-manual-finish committed `HEAD`
- downstream review stages still interpret that state as workflow/branch compliance failure, even though the continuation itself is allowed by contract

This creates an internal pipeline contradiction:
- one part of the workflow allows continuation
- downstream review still demands strict final-HEAD alignment with no compliant continuation evidence path

## Target Outcome
After implementation:
- the exact allowed manual-finish continuation path can reach downstream review stages with compliant final-HEAD semantics
- downstream stages either:
  1. accept the exact allowed final-HEAD lineage for the pinned continuation path, or
  2. fail closed with explicit deterministic evidence that final-HEAD compliance was not proven
- ordinary stale-head or generic descendant/ancestor cases remain rejected
- no rerun loop is reopened
- no orchestration scope is widened

## Atomic Task Isolation Contract
This story is intentionally narrow.

Allowed problem to solve:
- final-HEAD review compliance for the exact allowed manual-finish continuation case after `blocked_non_converging_rerun`

Not allowed:
- changing normal review eligibility rules
- changing run orchestration
- changing retry policy
- changing diff generation fidelity
- changing general operator guidance policy
- adding broad artifact refresh workflows
- changing escalation behavior

If implementation pressure suggests broader workflow redesign, stop and fail closed rather than expanding scope.

## Risks
- Scope drift into orchestration or rerun policy
- Accidental fail-open acceptance of stale or unrelated descendant `HEAD`
- Inconsistent interpretation across AI review, classification, gate, and analyze
- Regression in ordinary committed-head review path
- Hidden dependence on ad hoc workspace state instead of deterministic committed evidence

## Manual Actions
- Materialize this bundle pack
- Validate the materialized bundle
- Update registry status conservatively for US-AUTO-55
- Create a feature branch before implementation
- Commit story artifacts before run
- Run the story on the feature branch
- Analyze the resulting pinned run before any review-stage continuation

## Acceptance Notes
Acceptance requires all of the following:
1. Ordinary workflow still rejects `run -> commit -> review` without a fresh committed-head rerun.
2. Exact allowed manual-finish continuation after `blocked_non_converging_rerun` can produce compliant downstream review behavior for final branch `HEAD`.
3. If final-HEAD compliance cannot be proven, downstream stages fail closed with deterministic evidence/reasoning.
4. Ancestor-run, unrelated descendant, or generic stale-head variants remain rejected.
5. No diff fidelity regression is introduced.
6. No orchestration or retry behavior changes are introduced.
7. Tests cover both exact-allow and nearby-reject cases.

