# US-AUTO-45: Deterministic review gate artifact reuse

## Story ID and Title
- **Story ID:** US-AUTO-45
- **Title:** Deterministic review gate artifact reuse

## Objective
Make `automation/scripts/review_gate_story_run.sh` deterministic for a pinned run by requiring it to consume existing pinned review artifacts as the single source of truth instead of recomputing or implicitly regenerating review/classification state.

## Scope
- Harden `automation/scripts/review_gate_story_run.sh` so it reuses pinned run artifacts only.
- Fail closed when required pinned artifacts are missing, invalid, or inconsistent for the selected run.
- Keep `AUTOMATION_RUN_DIR` and pinned-run semantics explicit and deterministic.
- Update `automation/scripts/analyze_story_run.sh` if needed so operator guidance reflects the stricter gate contract.
- Add or update focused tests for deterministic artifact reuse and fail-closed behavior.
- Update workflow docs to state that review gate consumes existing artifacts and must not recompute them.

## Non-goals
- Do not introduce a new review artifact format.
- Do not broaden scope into bundle generation or materialization.
- Do not relax fail-closed safety checks.
- Do not add reverse sync from active bundle to bundle pack.
- Do not modify AI review or classification producer behavior in this story.

## Dependencies
- Existing pinned run contract under `automation/runs/<STORY_ID>/<RUN_ID>/`.
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- Existing merge recommendation contract and stale-run/head-consistency checks.

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- Existing pinned run artifacts for the selected run:
  - `ai_review_result.md`
  - `review_classification.md`
  - `review_gate_result.json`
  - `manifest.md`
  - `run_meta.txt`

## Current Code Reality
- Operator evidence shows manual `ai_review_story_run.sh` and `classify_review_story_run.sh` can produce approve for a pinned run, while `review_gate_story_run.sh` later produces reject for the same run.
- This means review gate is not yet acting as a strict consumer of pinned artifacts and allows recomputation drift or inconsistent evidence reuse.
- Downstream operator trust is reduced because a pinned run cannot currently be treated as immutable source-of-truth evidence.

## Target Outcome
- For a pinned run with valid existing `ai_review_result.md` and `review_classification.md`, `review_gate_story_run.sh` consumes those artifacts only.
- Gate must not rerun AI review or classification.
- If required artifacts are missing or invalid for the pinned run, gate fails closed with deterministic remediation.
- Operator analysis clearly states that gate is reusing pinned artifacts and whether the run is ready for gate execution.

