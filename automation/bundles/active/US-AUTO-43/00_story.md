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
- AI review outputs are not consistently validated
- classification may run on invalid inputs
- failure states are implicit and not classified
- debugging requires manual inspection

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

