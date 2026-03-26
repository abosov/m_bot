# Story Bundle Pack
Story-ID: US-AUTO-45
Version: 1

=== FILE: 00_story.md ===
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

=== FILE: 01_context_bundle.md ===
# US-AUTO-45: Context Bundle

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- Pinned run evidence under `automation/runs/<STORY_ID>/<RUN_ID>/`

## Current Code Reality
- The current review pipeline is supposed to allow operators to pin a run directory and then execute review, classification, and gate against that exact evidence set.
- In practice, the same pinned run can lead to different final outcomes: manual AI review plus classification may produce approve, while `review_gate_story_run.sh` later yields reject.
- This indicates the pinned run is not yet being treated as immutable source-of-truth evidence at the gate boundary.

## Architectural Intent
- Make review gate a strict consumer of already-produced pinned review artifacts.
- Preserve fail-closed behavior when evidence is missing or invalid.
- Preserve pinned-run selection via `AUTOMATION_RUN_DIR`.
- Preserve stale-run and head-consistency protections.
- Keep implementation limited to gate artifact consumption, operator analysis, tests, and docs.

## Risks
- If hidden fallback or recomputation logic still exists, nondeterminism may remain.
- If docs or analyze output still imply gate can regenerate upstream artifacts, operator behavior may remain inconsistent.
- If this story broadens into producer-script changes, it will exceed the intended scope.

## Acceptance Notes
- Bundle content must be fully resolved with no duplicated file sections and no placeholder tokens.
- Gate must consume existing pinned artifacts and must not implicitly regenerate them.
- Missing or invalid pinned artifacts must produce deterministic fail-closed behavior.
- Analyze and docs must align with the stricter pinned-artifact gate contract.
- Reverse sync and bundle-pack tooling changes remain out of scope for this story.

=== FILE: 02_file_scope.md ===
# US-AUTO-45: File Scope

## Files Allowed To Change
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `tests/test_review_gate_story_run.py`
- `tests/test_analyze_story_run.py`
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Files Not Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/scripts/commit_story_artifacts.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/build_bundle_pack.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/run_codex_task.sh`
- `automation/scripts/check_allowed_files.sh`
- `automation/scripts/merge_recommendation_contract.sh`
- `automation/bundle_packs/US-AUTO-46.bundle.md`

## Scope Notes
- The issue to solve is deterministic reuse at gate time, not upstream run or materialization behavior.
- AI review and classification producers should remain unchanged; this story constrains gate as consumer.
- Reverse sync and bundle-pack tooling are explicitly deferred to US-AUTO-46.
- If tests reveal that gate determinism cannot be fixed without changing upstream producers, stop and record a follow-up instead of broadening scope.

=== FILE: 03_master_prompt.md ===
# US-AUTO-45: Master Prompt

## Role
You are the System Architect + Developer + QA + Security Reviewer for Zumbot.

## Goal
Make `automation/scripts/review_gate_story_run.sh` deterministic by forcing it to consume pinned run review artifacts as source of truth and fail closed when those prerequisites are missing or invalid, without recomputing upstream review or classification stages.

## Source of Truth
- `automation/bundles/active/US-AUTO-45/00_story.md`
- `automation/bundles/active/US-AUTO-45/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-45/02_file_scope.md`
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- Existing pinned run artifacts for the selected run

## Files Allowed To Change
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `tests/test_review_gate_story_run.py`
- `tests/test_analyze_story_run.py`
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Files Not Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/scripts/commit_story_artifacts.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/build_bundle_pack.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/run_codex_task.sh`
- `automation/scripts/check_allowed_files.sh`
- `automation/scripts/merge_recommendation_contract.sh`

## Implementation Rules
- Keep the patch minimal and story-scoped.
- Do not invent new artifact formats.
- Do not silently recover by recomputing upstream artifacts.
- Preserve fail-closed behavior.
- Preserve pinned-run and stale-head protections.
- If an out-of-scope dependency is discovered, record it as a follow-up instead of implementing it here.
- Explicitly restate the one-sentence task intent before edits.
- Do not broaden scope beyond declared intent.

## Execution Gate
- Refuse implementation if this story would require upstream producer changes.
- Refuse implementation if deterministic reuse cannot be enforced within the allowed files.
- Refuse implementation if a second independently reviewable fix would need to be bundled into this run.

## Test Plan
- Add or update focused tests for deterministic reuse.
- Add or update focused tests for missing-artifact fail-closed behavior.
- Add or update focused tests for no-recompute expectations.
- Run targeted pytest for touched gate and analyze tests.

## Output
Return:
1. changed files summary
2. implementation rationale
3. exact lifecycle integration points used
4. tests run and results
5. risks or follow-ups discovered but not implemented
6. final diff summary

=== FILE: 04_review_checklist.md ===
# US-AUTO-45: Review Checklist

## Scope Validation
- [ ] Changes stay inside `02_file_scope.md`
- [ ] No forbidden files changed
- [ ] No unrelated refactor or formatting-only edits
- [ ] No producer-script or materialization scope creep was introduced

## Functional Validation
- [ ] `review_gate_story_run.sh` consumes pinned artifacts only
- [ ] Gate does not invoke AI review or classification stages
- [ ] Missing pinned artifacts cause fail-closed behavior
- [ ] Invalid pinned classification causes fail-closed behavior
- [ ] The same pinned evidence produces the same gate outcome

## Architecture Validation
- [ ] Review gate acts as an evidence consumer, not an upstream recomputation stage
- [ ] Pinned-run semantics remain explicit
- [ ] Stale-run and head-consistency protections remain intact
- [ ] Docs and operator guidance stay aligned with the stricter contract

## Verification
- [ ] Focused tests updated
- [ ] Validation commands are recorded
- [ ] Manual verification steps are recorded when needed
- [ ] Risks and follow-ups are captured before merge

## Review Prompt Seed
- Verify that gate behavior is deterministic for a pinned run with valid existing review artifacts.
- Verify that missing or invalid artifacts produce deterministic fail-closed behavior.
- Verify that no implicit recomputation path remains.

=== FILE: 05_followups.md ===
# US-AUTO-45: Follow-Ups

## Follow-Up Prompt Queue
- `US-AUTO-46` — Reverse sync active bundle to bundle pack
- `<none yet beyond known adjacent follow-up>`

## Iteration Notes
- Keep this story focused on deterministic pinned-artifact reuse at gate time only.
- Do not mix in reverse sync, materialization redesign, or producer-stage behavior changes.
- If implementation discovers hidden upstream dependencies, record them as a separate follow-up rather than widening this story.

## Follow-Up Prompt Template
- Story ID
- single finding or blocker
- exact allowed files
- exact forbidden files
- minimal test target
- explicit residual risk

## PR Description Template
- Summary
- Story Context
- Scope
- Files Changed
- Tests
- Risks / Notes

=== FILE: 06_manual_actions.md ===
# US-AUTO-45: Manual Actions

## Required Human Actions
- Materialize the bundle pack for `US-AUTO-45`.
- Validate the materialized active bundle before any run.
- Review the active bundle files in Cursor before executing the story.
- If validator fails, fix the bundle pack first instead of patching active files manually.

## Execution Notes
- Bundle pack source of truth: `automation/bundle_packs/US-AUTO-45.bundle.md`
- Materialize with: `automation/scripts/materialize_story_bundle.sh US-AUTO-45`
- Validate with: `automation/scripts/validate_story_bundle.sh US-AUTO-45`
- Open active files after successful validation:
  - `automation/bundles/active/US-AUTO-45/00_story.md`
  - `automation/bundles/active/US-AUTO-45/02_file_scope.md`
  - `automation/bundles/active/US-AUTO-45/03_master_prompt.md`

## Completion Status
- [ ] No manual actions required
- [ ] Manual actions completed and documented

## Additional Manual Verification
- Confirm the bundle contains exactly seven file sections.
- Confirm there are no nested `=== FILE: ... ===` markers inside section bodies.
- Confirm validation passes before `run_story.sh`.