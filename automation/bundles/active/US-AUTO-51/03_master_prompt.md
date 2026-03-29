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

