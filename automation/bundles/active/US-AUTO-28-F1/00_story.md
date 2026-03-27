# US-AUTO-28-F1 — Escalation input validation hardening (fail-closed, production)

## Story ID and Title
- **Story ID:** US-AUTO-28-F1
- **Title:** Escalation input validation hardening (fail-closed, production)

## Objective
Establish a strict, deterministic, fail-closed validation contract for `escalation_result.json` so that no malformed, inconsistent, or tampered escalation artifact can influence pipeline execution.

## Scope
In scope:
- strict JSON parsing (no regex/sed or partial parsing)
- required schema validation for escalation artifact
- enforce allowed values and transitions
- origin validation (story_id, run_id, path binding)
- deterministic failure classification and messaging
- regression tests for all invalid cases

Out of scope:
- changes to review/classify/gate scripts
- escalation UX or retry strategy
- cryptographic integrity (future follow-up)

## Non-goals
- no fallback or auto-repair
- no silent coercion of values
- no expansion of escalation semantics

## Dependencies
- US-AUTO-28 (anti-cycle enforcement layer, active)
- US-AUTO-42 (fail-closed resolution_action)

## Source of Truth
- automation/scripts/run_story.sh (escalation handling)
- Epic registry contract (US-AUTO)

## Current Code Reality
- escalation artifact may be parsed via weak methods
- missing schema validation
- origin consistency not enforced
- potential for spoofed or stale artifacts

## Target Outcome
Escalation artifact is accepted ONLY if ALL conditions hold:
- valid JSON (strict parse)
- required fields present
- values conform to contract
- status transition is valid
- origin matches current STORY_ID and RUN_ID

Otherwise:
→ immediate FAIL (fail-closed)
→ deterministic error classification

## Atomic Task Isolation Contract
- single responsibility: escalation input validation
- no modification of escalation semantics
- no cross-stage logic
- no fallback behavior
- hard stop on violation

## Validation Contract

Required schema:
- status: string (must be "pending")
- resolution_action: string (non-empty, allowed set)
- story_id: string (must equal current STORY_ID)
- run_id: string (must equal current RUN_ID)

Allowed resolution_action values:
- retry
- abort
- manual_intervention

Invalid cases (FAIL):
- malformed JSON
- missing fields
- empty resolution_action
- unknown resolution_action
- status != "pending"
- story_id mismatch
- run_id mismatch

## Pipeline Invariants
- escalation cannot be bypassed
- escalation cannot be spoofed via file modification
- escalation must always be validated before execution
- no escalation decision is trusted without validation

## Observability
On failure:
- print deterministic error code:
  - ESCALATION_INVALID_JSON
  - ESCALATION_MISSING_FIELDS
  - ESCALATION_INVALID_STATUS
  - ESCALATION_INVALID_ACTION
  - ESCALATION_ORIGIN_MISMATCH
- log failure in run output (stdout/stderr)
- ensure analyze_story_run.sh can detect failure reason

## Risks
- Medium regression risk due to stricter validation
- Possible breakage of previously tolerated invalid artifacts
- Expected and acceptable as part of hardening

## Manual Actions
- none required

## Acceptance Notes
- all invalid escalation artifacts fail deterministically
- no regex/sed parsing remains
- validation fully enforced before escalation logic executes
- tests cover all failure modes

---

