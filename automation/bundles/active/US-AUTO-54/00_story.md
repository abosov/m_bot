## Story ID and Title
US-AUTO-54 — Committed-HEAD review diff fidelity for US-AUTO-28-F1 rerun artifacts

## Objective
Restore deterministic `review_gate_story_run.sh` fidelity for the exact committed-head rerun path reproduced by `US-AUTO-28-F1`, so `review_diff_patch_mismatch` is emitted only when the pinned rerun evidence is truly stale or inconsistent.

The story is intentionally narrow: diagnose and fix the review-boundary comparison for the exact rerun-artifact path that still rejects after a clean committed-head rerun with matching manifest HEAD.

## Scope
In scope:
- inspect and correct the committed-head rerun diff comparison logic at the review gate boundary
- keep the change limited to the exact rerun-artifact fidelity path used by `review_gate_story_run.sh`
- add focused regression coverage for the reproduced `US-AUTO-28-F1` rerun case and for at least one true mismatch case that must still reject
- preserve fail-closed behavior and current external reject semantics outside the exact defect being fixed

Out of scope:
- new orchestration stages
- retry logic, rerun automation, continuation policy, escalation policy, or operator UX redesign
- broad refactors across unrelated pipeline scripts
- changing review classification policy or relaxing review boundary guards
- reopening `US-AUTO-28-F1` implementation scope

## Non-goals
- do not change `run_story.sh`
- do not widen `run_codex_task.sh` scope unless strictly required to preserve committed-head rerun diff fidelity and supported by failing evidence
- do not alter manual-finish continuation semantics from `US-AUTO-52`
- do not change bundle validator behavior
- do not convert governance rejects into approvals

## Dependencies
- US-AUTO-46 — review operates strictly on committed HEAD
- US-AUTO-47 — rerun convergence boundary
- US-AUTO-50 — structured AI review contract and stable diff/story-artifact filtering baseline
- US-AUTO-52 — strict manual-finish continuation contract
- US-AUTO-53 — committed-HEAD `diff.patch` review fidelity baseline
- US-AUTO-28-F1 — reproduced committed-head rerun path that exposed the remaining blocker

## Source of Truth
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/scripts/review_gate_story_run.sh`
- `tests/test_review_gate_story_run.py`
- pinned committed-head rerun evidence model already established by the `US-AUTO-28-F1` observation recorded in the registry
- existing review-boundary invariants already merged on `main`

## Current Code Reality
The registry records that `US-AUTO-28-F1` implementation is complete and that the remaining blocker is a downstream committed-head review artifact fidelity issue on rerun artifacts, specifically a `review_diff_patch_mismatch` rejection after a clean committed-head rerun with matching manifest HEAD.

`US-AUTO-53` already hardened committed-head `diff.patch` generation so downstream review compares the committed implementation diff represented by the pinned run. Despite that, the exact `US-AUTO-28-F1` rerun path can still reject in `review_gate_story_run.sh`, which means a narrower rerun-artifact comparison defect remains at the review boundary.

The current story must therefore stay tightly constrained to the review gate’s handling of pinned rerun artifacts and must not reopen unrelated runtime or orchestration behavior.

## Target Outcome
After implementation:
- a clean committed-head rerun with matching manifest HEAD and matching committed implementation diff for the exact `US-AUTO-28-F1` style rerun path no longer rejects with `review_diff_patch_mismatch`
- true mismatch cases still reject deterministically with the existing fail-closed behavior
- external contracts remain stable unless the existing defect makes a contract-preserving correction necessary
- regression coverage proves both acceptance of the exact good rerun path and rejection of real mismatch paths

## Atomic Task Isolation Contract
This story is atomic and must remain atomic.

Hard boundaries:
- solve exactly one problem: review-gate diff fidelity for the exact committed-head rerun artifact path
- restrict implementation to the minimum code and tests needed to correct that defect
- do not combine validation redesign, retry policy, escalation logic, UX improvements, or bundle governance changes into this story
- if a broader issue is discovered, stop at the narrowest safe fix and record the remainder in follow-ups instead of widening the story

Fail-closed requirement:
- when evidence is incomplete, stale, malformed, or ambiguous, the pipeline must still reject rather than silently accept
- the fix must reduce false mismatch on the reproduced rerun path without introducing fail-open behavior

## Risks
- **Complexity:** Medium
- **Risk:** Medium
- **Blast Radius:** Narrow

Primary risks:
- scope drift into broader review or orchestration logic
- accidentally weakening true mismatch rejection behavior
- coupling the fix to `US-AUTO-28-F1` in a way that is too bespoke instead of correcting the exact review-boundary invariant
- regression in review gate evidence handling for already-stable stories

Mitigations:
- keep file scope narrow
- preserve existing reject semantics for malformed or stale evidence
- add focused tests for exact accept and reject boundaries
- avoid touching unrelated scripts unless failing evidence proves they are the true defect source

## Manual Actions
- update the registry entry for `US-AUTO-54` from `Planned` to `Bundle Drafted` when this bundle is materialized and validated
- keep `US-AUTO-28-F1` as `Implemented`
- keep `US-AUTO-54` as the next recommended story until the implementation lands and is merged
- if the investigation reveals a broader issue than review-gate rerun fidelity, split that broader issue into a new follow-up instead of widening this story

## Acceptance Notes
This story is complete only if all of the following are true:
- the bundle materializes and validates cleanly
- the implementation remains within the declared file scope
- a focused regression test reproduces the clean committed-head rerun acceptance case
- a focused regression test proves a real mismatch still rejects
- the final behavior remains fail-closed for malformed, stale, or inconsistent rerun evidence
- no unrelated runtime or orchestration behavior is changed as part of this story

