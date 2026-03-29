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

