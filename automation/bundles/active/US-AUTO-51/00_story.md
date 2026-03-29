# US-AUTO-51 — Manual-finish review continuation contract

## Story ID and Title
- **Story ID:** `US-AUTO-51`
- **Title:** `Manual-finish review continuation contract`

## Objective
Establish a deterministic, fail-closed continuation contract for the review chain after a non-converging rerun was manually finished and committed to `HEAD`, so pinned run artifacts can continue through classify and gate without being rejected as stale solely because `manifest HEAD != checkout HEAD`.

## Scope
In scope:
- Define the exact continuation boundary for manual-finish review on committed `HEAD`.
- Align `analyze_story_run.sh`, `classify_review_story_run.sh`, and `review_gate_story_run.sh` to the same rule.
- Allow continuation only for the narrow manual-finish case produced by a confirmed non-converging rerun boundary.
- Preserve strict fail-closed behavior for all other stale-run situations.
- Preserve gate fidelity checks against the authoritative `review_artifact_base..HEAD` diff.
- Add focused regression tests for allowed continuation and blocked stale-evidence cases.
- Update workflow documentation and epic registry references for the new contract.

Not in scope:
- Changes to `automation/scripts/run_story.sh`.
- Changes to `automation/run_codex_task.sh`.
- Changes to `automation/scripts/ai_review_story_run.sh`.
- Rerun convergence redesign beyond the already implemented US-AUTO-47 boundary.
- Runner redesign, auto-commit behavior, or bundle/materialize/validate workflow redesign.
- Broad operator UX improvements.
- Any changes to escalation policy itself (`US-AUTO-28`, `US-AUTO-28-F1` logic, or escalation schema semantics).

## Non-goals
- Do not weaken the committed-HEAD review boundary introduced by US-AUTO-46.
- Do not allow arbitrary stale runs to continue.
- Do not silently regenerate run artifacts.
- Do not treat descendant `HEAD` as review-valid unless the pinned run is a confirmed non-converging rerun/manual-finish continuation case.
- Do not broaden into review prompt redesign, retry logic, caching, or expensive-run controls.
- Do not finish `US-AUTO-28-F1` in this story.

## Dependencies
- `US-AUTO-46` — committed-HEAD review fidelity.
- `US-AUTO-47` — non-converging rerun / manual-finish boundary.
- `US-AUTO-48` — AI review artifact contract hardening.
- `US-AUTO-49` — scope-baseline fix for active-story committed artifacts.
- `US-AUTO-50` — structured AI review output contract.
- Parked implementation branch for `US-AUTO-28-F1`: `feat/us-auto-28-f1-run` at manual-finish commit `607bed0`.

## Source of Truth
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `tests/test_analyze_story_run.py`
- `tests/test_classify_review_story_run.py`
- `tests/test_review_gate_story_run.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Current Code Reality
- US-AUTO-47 introduced a manual-finish path for non-converging reruns.
- `analyze_story_run.sh` already partially recognizes the special case and can print `RUN STATUS: READY (manual finish committed; review can continue on current HEAD)` for a clean checkout.
- Downstream continuation is still inconsistent:
  - `classify_review_story_run.sh` fails closed on `review_head_mismatch`.
  - `review_gate_story_run.sh` fails closed on `review_head_mismatch`.
  - `analyze_story_run.sh` can revert back to generic stale-run blocking once downstream artifacts exist, creating contradictory operator guidance.
- `US-AUTO-28-F1` is blocked specifically because manual-finish continuation exists in principle but not as a fully aligned downstream contract.

## Target Outcome
- One narrow continuation rule exists across analyze / classify / gate:
  - **Allowed only when** the selected run is the latest confirmed non-converging rerun evidence set and current checkout `HEAD` is the committed manual-finish continuation of that exact run path.
  - **Blocked for everything else** when run-manifest HEAD does not match current checkout HEAD.
- `analyze_story_run.sh` reports a stable continuation-ready state before and after downstream artifacts are created.
- `classify_review_story_run.sh` can classify the pinned AI review artifact in the manual-finish continuation case without treating the run as generically stale.
- `review_gate_story_run.sh` can evaluate the pinned run in the manual-finish continuation case while still enforcing diff fidelity and all existing fail-closed checks.
- `US-AUTO-28-F1` can resume from the parked branch after this story merges, without rerunning `run_story.sh` again.

## Atomic Task Isolation Contract
### Single Purpose
Make manual-finish continuation a first-class, fail-closed downstream review contract for analyze / classify / gate.

### Intent
Unify the post-manual-finish continuation rule so a confirmed non-converging rerun can continue through pinned review artifacts on the committed manual-finish `HEAD`, while preserving strict rejection for all other stale-run cases.

### Out-of-Scope
- `run_story.sh`
- `run_codex_task.sh`
- `ai_review_story_run.sh`
- runner redesign
- convergence engine redesign
- escalation logic redesign
- operator UX polish beyond exact continuation guidance
- parked implementation merge itself

### Hard Stop Rules
- If implementation would require broad runner redesign, stop.
- If implementation would require weakening generic stale-head rejection, stop.
- If implementation would require bypassing fidelity checks in gate, stop.
- If implementation would require silent artifact regeneration, stop.

### Follow-Up Rule
Any broader cleanup, helper extraction, or generalized stale-run policy work must be captured as a separate follow-up story.

## Risks
- False-positive continuation if the special-case guard is too broad.
- Regression where generic stale-run rejection becomes permissive.
- Divergence between analyze messaging and classify/gate enforcement.
- Misinterpretation of descendant `HEAD` as sufficient without artifact fidelity.
- Accidental absorption of `US-AUTO-28-F1` implementation work into this contract story.

## Manual Actions
- Create and materialize the bundle pack for `US-AUTO-51`.
- Update the epic registry to add `US-AUTO-51` as the active blocker follow-up and keep `US-AUTO-28-F1` parked/blocked.
- Run focused tests only for analyze / classify / gate behavior.
- After merge of `US-AUTO-51`, return to `feat/us-auto-28-f1-run`, rebase or merge `main`, and continue from the pinned parked run instead of rerunning `run_story.sh`.

## Acceptance Notes
- Generic stale-run mismatch remains fail-closed.
- Manual-finish continuation is accepted only for the exact US-AUTO-47-style non-converging rerun case.
- Analyze output stays stable and non-contradictory after downstream artifacts appear.
- Classification and gate are continuation-capable on committed manual-finish `HEAD`.
- Gate fidelity checks remain mandatory and unchanged in strength.
- `US-AUTO-28-F1` remains blocked until this story merges, then becomes resumable from the parked branch.

