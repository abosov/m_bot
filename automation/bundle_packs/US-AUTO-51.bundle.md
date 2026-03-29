# Story Bundle Pack
Story-ID: US-AUTO-51
Version: 1

=== FILE: 00_story.md ===
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

=== FILE: 01_context_bundle.md ===
# US-AUTO-51 — Context Bundle

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
- The epic registry now records `US-AUTO-28-F1` as blocked pending a manual-finish review continuation follow-up.
- US-AUTO-47 solved the rerun loop boundary, but not the downstream continuation contract.
- `analyze_story_run.sh` already contains a partial special-case for manual-finish continuation, but downstream stage logic still hard-rejects head mismatch.
- `review_gate_story_run.sh` correctly preserves strict fidelity enforcement and currently rejects `review_head_mismatch` before consuming pinned artifacts.
- The missing piece is not fresh rerun logic; it is a narrow, downstream continuation rule for the already-finished manual-finish path.

## Architectural Intent
- Preserve the committed-HEAD boundary as the default rule.
- Introduce one explicit exception path:
  - selected run is the latest confirmed non-converging rerun evidence;
  - current checkout `HEAD` is the committed manual-finish continuation;
  - working tree is clean;
  - pinned run artifacts remain the same run evidence;
  - gate still validates authoritative diff fidelity against current `HEAD`.
- Keep the solution localized to analyze / classify / gate and their direct tests.
- Keep operator semantics deterministic:
  - either the pinned run is continuation-valid,
  - or it is stale and blocked.

## Risks
- Scope drift into run-stage or AI review-stage behavior.
- Duplicated ad hoc continuation logic across scripts.
- Weakening fail-closed semantics by treating any descendant `HEAD` as acceptable.
- Hidden contradiction between printed analyze status and actual executable downstream behavior.
- Confusion between continuation contract and escalation/governance stories.

## Acceptance Notes
- The bundle must stay atomic and focused on downstream continuation only.
- File scope and master prompt must match exactly.
- Review checklist must reject any patch that broadens the stale-run exception beyond the manual-finish continuation case.
- Registry update logic must explicitly keep `US-AUTO-28-F1` parked until `US-AUTO-51` is merged.

=== FILE: 02_file_scope.md ===
# US-AUTO-51 — File Scope

## Files Allowed To Change
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `tests/test_analyze_story_run.py`
- `tests/test_classify_review_story_run.py`
- `tests/test_review_gate_story_run.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/US-AUTO-51.bundle.md`
- `automation/bundles/active/US-AUTO-51/**`

## Files Not Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/run_codex_task.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/finalize_story.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `tests/test_run_story.py`
- `tests/test_run_codex_task.py`
- `tests/test_ai_review_story_run.py`
- `backend/**`
- `frontend/**`
- `database/**`
- `migrations/**`
- `.github/workflows/**`
- unrelated bundle packs
- the parked implementation branch contents for `US-AUTO-28-F1`

## Scope Notes
- Keep this story narrowly focused on downstream continuation after manual finish.
- Do not redesign rerun detection.
- Do not redesign AI review generation or validation.
- Do not absorb `US-AUTO-28-F1` implementation changes into this story.
- Allowed change types:
  - narrow continuation predicate logic;
  - aligned operator/analyze messaging;
  - direct regression tests;
  - minimal documentation and registry updates required by the new contract.
- Hard anti-scope-drift rule:
  - if a patch changes run-stage behavior, AI review-stage behavior, or generic stale-head semantics outside the manual-finish continuation case, reject it.

=== FILE: 03_master_prompt.md ===
# US-AUTO-51 PROMPT 1 — Manual-Finish Review Continuation Contract

## Role
You are the Zumbot workflow automation engineer working under the repository’s CODEX Operating System.

## Goal
Implement a fail-closed downstream continuation contract so a confirmed non-converging rerun that was manually finished and committed to `HEAD` can continue through pinned analyze / classify / gate behavior without being rejected as generic stale-run evidence, while all non-manual-finish stale-run cases remain blocked.

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
- `automation/bundles/active/US-AUTO-51/**`

## Files Allowed To Change
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `tests/test_analyze_story_run.py`
- `tests/test_classify_review_story_run.py`
- `tests/test_review_gate_story_run.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/US-AUTO-51.bundle.md`
- `automation/bundles/active/US-AUTO-51/**`

## Files Not Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/run_codex_task.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/finalize_story.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `tests/test_run_story.py`
- `tests/test_run_codex_task.py`
- `tests/test_ai_review_story_run.py`
- `backend/**`
- `frontend/**`
- `database/**`
- `migrations/**`
- `.github/workflows/**`
- unrelated bundle packs
- the parked implementation branch contents for `US-AUTO-28-F1`

## Atomic Task Isolation Contract
- **Single purpose:** downstream manual-finish continuation contract for analyze / classify / gate.
- **Intent statement:** allow continuation only for the exact committed manual-finish case produced by a confirmed non-converging rerun, and keep all other stale-run mismatch cases fail-closed.
- **Out of scope:** run-stage changes, AI review-stage changes, runner redesign, convergence redesign, escalation redesign, parked implementation merge work.
- **Hard stop:** if implementation requires weakening generic stale-run rejection, redesigning run generation, or bypassing fidelity checks, stop and leave a focused follow-up.
- **Minimal patch rule:** prefer the smallest deterministic change set that aligns analyze / classify / gate semantics and their direct tests.
- **No hidden fallbacks:** do not silently rerun upstream stages, regenerate artifacts, or infer approval from unverified state.

## Execution Gate
1. Read the existing manual-finish boundary behavior in `analyze_story_run.sh`.
2. Read the current head-mismatch handling in `classify_review_story_run.sh` and `review_gate_story_run.sh`.
3. Implement one shared logical contract across these downstream stages:
   - generic `manifest HEAD != checkout HEAD` stays blocked;
   - special-case continuation is permitted only for confirmed non-converging rerun manual-finish continuation on committed clean `HEAD`.
4. Preserve existing clean-tree requirements.
5. Preserve existing artifact-fidelity enforcement in gate.
6. Update direct tests only for the exact continuation contract.
7. Update registry and checklist text minimally and accurately.

## Implementation Requirements
1. `analyze_story_run.sh` must continue to recognize manual-finish continuation after downstream artifacts exist, without falling back to contradictory stale-run messaging.
2. `classify_review_story_run.sh` must allow continuation for the narrow manual-finish case instead of rejecting `review_head_mismatch` generically.
3. `review_gate_story_run.sh` must allow continuation for the same narrow manual-finish case, but must still enforce diff fidelity and all existing fail-closed artifact checks.
4. Any allowed continuation path must still require a clean working tree.
5. Any non-manual-finish head mismatch must remain blocked / rejected deterministically.
6. Add focused regression tests for:
   - analyze continuation-ready state after manual finish;
   - classify allowed continuation after manual finish;
   - gate allowed continuation after manual finish when fidelity is preserved;
   - generic stale-run mismatch still blocked.
7. Update `docs/90_codex/STORY_EXECUTION_CHECKLIST.md` so the manual-finish continuation path is explicit and non-contradictory.
8. Update `docs/90_codex/epics/US-AUTO_REGISTRY.md` to add `US-AUTO-51` and keep `US-AUTO-28-F1` blocked pending this story’s merge.

## Verification Requirements
- `pytest -q tests/test_analyze_story_run.py`
- `pytest -q tests/test_classify_review_story_run.py`
- `pytest -q tests/test_review_gate_story_run.py`
- Analyze output stays continuation-ready for the manual-finish path even after downstream artifacts are present.
- Classification no longer rejects the exact manual-finish continuation case.
- Gate no longer rejects the exact manual-finish continuation case solely because of head mismatch.
- Gate still rejects generic stale-run mismatch.
- Gate still enforces authoritative diff fidelity.
- No files outside the allowed scope are modified.

## Output
Return:
1. changed files summary
2. design rationale
3. verification performed
4. risks / follow-ups
5. final diff

=== FILE: 04_review_checklist.md ===
# US-AUTO-51 — Review Checklist

## Scope Validation
- [ ] Only downstream continuation files changed: analyze / classify / gate, their direct tests, and minimal docs/registry updates.
- [ ] No changes were made to `run_story.sh`, `run_codex_task.sh`, or `ai_review_story_run.sh`.
- [ ] No changes were made outside the explicit allowed file list.
- [ ] The patch does not absorb `US-AUTO-28-F1` implementation work.

## Functional Validation
- [ ] Manual-finish continuation is allowed only for the exact confirmed non-converging rerun case.
- [ ] Generic stale-run mismatch remains fail-closed.
- [ ] Analyze messaging remains stable before and after downstream artifacts exist.
- [ ] Classification can continue on committed manual-finish `HEAD`.
- [ ] Gate can continue on committed manual-finish `HEAD`.
- [ ] Gate still enforces authoritative diff fidelity against current `HEAD`.
- [ ] Clean working tree remains mandatory.

## Verification
- [ ] `pytest -q tests/test_analyze_story_run.py`
- [ ] `pytest -q tests/test_classify_review_story_run.py`
- [ ] `pytest -q tests/test_review_gate_story_run.py`
- [ ] Manual-finish continuation case passes with pinned artifacts.
- [ ] Generic stale-run mismatch case still rejects deterministically.
- [ ] Registry and checklist docs updated consistently.

## HARD BLOCK
- [ ] REJECT if the stale-run exception becomes broader than the exact manual-finish continuation case.
- [ ] REJECT if gate fidelity checks are weakened or bypassed.
- [ ] REJECT if upstream run or AI review behavior is changed.
- [ ] REJECT if analyze text says continuation is allowed but classify/gate still reject the same exact case.
- [ ] REJECT if the patch relies on silent artifact regeneration or hidden reruns.

=== FILE: 05_followups.md ===
# US-AUTO-51 — Follow-Ups

## Follow-Up Prompt Queue
- `TBD` — Extract a shared helper for manual-finish continuation detection if the final patch duplicates the same predicate across scripts.
- `TBD` — Add a richer operator evidence summary that explicitly prints why a continuation-qualified manual finish is safe.
- `TBD` — Consider whether manual-finish continuation should be recorded explicitly in downstream result artifacts for later auditability.
- `TBD` — After `US-AUTO-28-F1` is merged, assess whether additional operator UX cleanup is still needed or whether the contract is sufficient.

## Iteration Notes
- Keep this story atomic: downstream continuation contract only.
- Do not reopen the rerun-boundary design from US-AUTO-47.
- Do not absorb AI review prompt or normalization work from US-AUTO-50 / US-AUTO-48.
- Do not generalize into descendant-HEAD review semantics outside the manual-finish continuation case.
- If a broader stale-run lifecycle redesign seems desirable, capture it as a separate follow-up rather than widening this story.

=== FILE: 06_manual_actions.md ===
# US-AUTO-51 — Manual Actions

## Required Human Actions
1. Create the bundle pack file:
   `automation/bundle_packs/US-AUTO-51.bundle.md`

2. Materialize the bundle:
   `automation/scripts/materialize_story_bundle.sh US-AUTO-51`

3. Validate the materialized bundle:
   `automation/scripts/validate_story_bundle.sh US-AUTO-51`

4. Update the epic registry during the story handoff:
   - add `US-AUTO-51` as a new P1 follow-up with status `Bundle Drafted` (or `In Progress` once work begins);
   - set `US-AUTO-51` as the effective blocker follow-up for the parked `US-AUTO-28-F1` path;
   - keep `US-AUTO-28-F1` status as `Blocked` with next action `Resume after US-AUTO-51 merges`;
   - keep `US-AUTO-50` as implemented / complete.

5. Create the feature branch:
   `git checkout -b feat/us-auto-51-manual-finish-review-continuation`

6. Commit the bundle artifacts before execution:
   - `automation/bundle_packs/US-AUTO-51.bundle.md`
   - `automation/bundles/active/US-AUTO-51/**`
   - registry/checklist updates required by this story

7. Run the story:
   `automation/scripts/run_story.sh US-AUTO-51`

8. Analyze the latest run:
   `automation/scripts/analyze_story_run.sh US-AUTO-51`

9. After merge of `US-AUTO-51`, return to the parked implementation branch:
   - checkout `feat/us-auto-28-f1-run`
   - update from latest `main`
   - continue review/classify/gate on the pinned parked run evidence without rerunning `automation/scripts/run_story.sh US-AUTO-28-F1`

## Completion Status
- [ ] Bundle created
- [ ] Bundle materialized
- [ ] Bundle validated
- [ ] Registry updated consistently
- [ ] Story artifacts committed before run
- [ ] Focused tests executed
- [ ] Post-merge handoff back to parked `US-AUTO-28-F1` prepared