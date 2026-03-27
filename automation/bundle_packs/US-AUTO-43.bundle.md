# Story Bundle Pack
Story-ID: US-AUTO-43
Version: 1

=== FILE: 00_story.md ===
# US-AUTO-43 — AI review failure handling and recovery contract

## Story ID and Title
- **Story ID:** US-AUTO-43
- **Title:** AI review failure handling and recovery contract

## Objective
Establish a strict, deterministic, and fail-closed contract for the AI review stage so that invalid AI review artifacts never propagate downstream and all failure states are explicitly detected, classified, and observable.

## Scope
In scope:
- enforce validation of AI review artifacts before classification
- introduce fail-closed behavior for missing, malformed, incomplete, or logically invalid outputs
- block classification if AI review validation fails
- ensure review gate never receives invalid classification input
- define deterministic failure states and observability

Out of scope:
- AI prompt improvements
- classification logic changes
- gate decision logic redesign
- retry/backoff mechanisms
- run orchestration changes

## Non-goals
- no fallback behavior
- no partial continuation
- no reconstruction of missing outputs
- no merging of responsibilities across stages

## Dependencies
- US-AUTO-39 — HEAD-bound review consistency
- US-AUTO-40 — review artifact fidelity
- US-AUTO-42 — fail-closed escalation resolution

## Source of Truth
- automation/scripts/ai_review_story_run.sh
- automation/scripts/classify_review_story_run.sh
- automation/scripts/review_gate_story_run.sh
- automation/scripts/analyze_story_run.sh
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md
- docs/90_codex/CODEX_OPERATING_SYSTEM.md

## Current Code Reality
- AI review outputs now enforce a strict fail-closed contract
- classification is blocked when AI review artifacts are missing, malformed, incomplete, or unreadable
- failure states are explicit through deterministic validation codes
- debugging no longer depends on parser stack traces for invalid artifacts

## Target Outcome
- AI review becomes a strict validation boundary
- invalid artifacts never reach classification
- failure modes are explicit and deterministic
- pipeline is strictly fail-closed at AI review stage

## Atomic Task Isolation Contract
### Single Purpose
Enforce fail-closed validation at AI review boundary.

### Exact Intent Statement
Implement strict validation and failure handling so classification cannot run on invalid AI review artifacts.

### Explicit Out-of-Scope
- classification redesign
- gate logic changes
- retry logic
- orchestration changes

### Allowed File Boundary
Defined in 02_file_scope.md.

### Forbidden File Boundary
Defined in 02_file_scope.md.

### Hard-Stop Condition
Stop if change requires modifying forbidden files or expanding scope.

### Follow-Up Rule
All additional issues must be captured in followups.

## Risks
- scope creep into classification/gate logic
- accidental fallback behavior
- incomplete validation coverage

## Manual Actions
- review bundle before execution
- validate bundle before run
- inspect failure scenarios manually

## Acceptance Notes
- classification MUST NOT run on invalid AI review
- all failure modes must be fail-closed
- behavior must be deterministic
- unreadable/non-UTF8 AI review artifacts must surface as `ai_review_unreadable_artifact`

=== FILE: 01_context_bundle.md ===
# US-AUTO-43: Context Bundle

## Source of Truth
- automation/scripts/ai_review_story_run.sh
- automation/scripts/classify_review_story_run.sh
- automation/scripts/review_gate_story_run.sh
- automation/scripts/analyze_story_run.sh

## Current Code Reality
- AI review validation is fail-closed across review/classify/gate/analyze
- invalid outputs cannot propagate to classification
- failure states are formally classified, including unreadable artifact handling

## Architectural Intent
- treat AI review as strict validation boundary
- enforce fail-closed behavior
- ensure deterministic pipeline behavior

## Risks
- scope drift into other pipeline stages
- incomplete validation
- hidden fallback paths

## Acceptance Notes
- validation enforced before classification
- failures block downstream execution
- behavior is deterministic

=== FILE: 02_file_scope.md ===
# US-AUTO-43: File Scope

## Files Allowed To Change
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `tests/test_ai_review_story_run.py`
- `tests/test_review_pipeline_validation_contract.py`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/US-AUTO-43.bundle.md`
- `automation/bundles/active/US-AUTO-43/**`

## Files Not Allowed To Change
- automation/scripts/run_story.sh
- automation/run_codex_task.sh
- automation/scripts/validate_story_bundle.sh
- automation/scripts/materialize_story_bundle.sh
- automation/scripts/story_change_ledger.sh
- backend/**
- frontend/**
- database/**

## Scope Notes
- only validation and failure handling changes allowed
- classification/gate logic must not change
- minimal patch only

=== FILE: 03_master_prompt.md ===
# US-AUTO-43 PROMPT 1 — AI Review Validation Contract

## Role
You are a Zumbot automation engineer enforcing strict pipeline governance.

## Goal
Ensure AI review stage enforces fail-closed validation so classification never runs on invalid artifacts.

## Source of Truth
- automation/scripts/ai_review_story_run.sh
- automation/scripts/classify_review_story_run.sh
- automation/scripts/review_gate_story_run.sh
- automation/scripts/analyze_story_run.sh

## Files Allowed To Change
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `tests/test_ai_review_story_run.py`
- `tests/test_review_pipeline_validation_contract.py`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/US-AUTO-43.bundle.md`
- `automation/bundles/active/US-AUTO-43/**`

## Files Not Allowed To Change
- automation/scripts/run_story.sh
- automation/run_codex_task.sh
- bundle system
- ledger
- git handling

## Output
Implement strict validation so:
- missing/malformed/incomplete outputs fail closed
- classification is blocked on invalid input
- failure states are deterministic and observable

=== FILE: 04_review_checklist.md ===
# US-AUTO-43: Review Checklist

## Scope Validation
- only allowed files changed
- no scope expansion
- no forbidden files touched

## Functional Validation
- invalid AI review blocks classification
- missing artifact triggers failure
- malformed output triggers failure
- incomplete output triggers failure
- unreadable/non-UTF8 output triggers failure
- logical invalidity triggers failure

## Verification
- tests cover all failure scenarios
- pipeline stops on invalid input
- behavior deterministic

=== FILE: 05_followups.md ===
# US-AUTO-43: Follow-Ups

## Follow-Up Prompt Queue
- <empty>

## Iteration Notes
- retry policy handled in separate story
- schema validation may be future enhancement

=== FILE: 06_manual_actions.md ===
# US-AUTO-43: Manual Actions

## Required Human Actions
- materialize bundle
- validate bundle
- review active bundle
- run story
- inspect failure scenarios

## Completion Status
- [ ] Bundle materialized
- [ ] Bundle validated
- [ ] Ready for run
