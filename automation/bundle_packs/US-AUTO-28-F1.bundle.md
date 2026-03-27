# Story Bundle Pack
Story-ID: US-AUTO-28-F1
Version: 1

=== FILE: 00_story.md ===
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

=== FILE: 01_context_bundle.md ===
# Context Bundle

## Source of Truth
- run_story.sh escalation logic
- US-AUTO-28 anti-cycle enforcement

## Current Code Reality
- escalation artifact not strictly validated
- possible acceptance of malformed or spoofed inputs

## Architectural Intent
- escalation must be deterministic and tamper-resistant
- validation must precede any decision
- pipeline must operate in fail-closed mode

## Risks
- escalation bypass via artifact manipulation
- inconsistent behavior across runs

## Acceptance Notes
- strict schema validation enforced
- no implicit trust of artifacts

---

=== FILE: 02_file_scope.md ===
# File Scope

## Files Allowed To Change
- automation/scripts/run_story.sh
- tests/test_run_story.py

## Files Not Allowed To Change
- automation/scripts/analyze_story_run.sh
- automation/scripts/review_gate_story_run.sh
- automation/scripts/classify_review_story_run.sh
- automation/scripts/commit_story_artifacts.sh
- automation/scripts/run_codex_task.sh
- any files under automation/runs/

## Scope Notes
- modify ONLY escalation validation block
- no refactoring outside validation
- no changes to unrelated logic
- no structural changes to pipeline

---

=== FILE: 03_master_prompt.md ===
# Master Prompt

## Role
You are a strict systems engineer enforcing fail-closed escalation validation in a deterministic pipeline.

## Goal
Ensure escalation input is fully validated, origin-bound, and cannot be spoofed or inconsistently applied.

## Source of Truth
- run_story.sh escalation handling
- US-AUTO pipeline contracts

## Files Allowed To Change
- automation/scripts/run_story.sh
- tests/test_run_story.py

## Files Not Allowed To Change
- all other files

## Atomic Task Isolation Contract
- one task only: escalation validation
- no fallback logic
- no scope expansion
- no cross-script changes
- hard stop on violation

## Execution Gate
FAIL if ANY:
- JSON invalid
- required field missing
- status != pending
- resolution_action invalid
- origin mismatch (story_id/run_id)

## Implementation Requirements
- use strict JSON parsing (python or equivalent)
- enforce schema validation
- validate allowed values
- enforce origin binding
- emit deterministic error messages

## Verification Requirements
tests must cover:
- malformed JSON
- missing fields
- invalid values
- origin mismatch
- valid case passes

## Output
- minimal deterministic patch
- no unrelated changes
- no refactoring

---

=== FILE: 04_review_checklist.md ===
# Review Checklist

## Scope Validation
- only allowed files modified
- only escalation validation logic changed

## Functional Validation
- strict JSON parsing used
- schema validation implemented
- origin validation present
- fail-closed enforced

## Verification

### HARD BLOCK
- regex/sed JSON parsing exists → REJECT
- missing schema validation → REJECT
- missing origin validation → REJECT
- fallback logic present → REJECT
- non-deterministic error handling → REJECT

### RESULT
- APPROVE only if all checks pass

---

=== FILE: 05_followups.md ===
# Follow-ups

## Follow-Up Prompt Queue
- US-AUTO-28-F2 — escalation artifact integrity (signature / hash binding)
- US-AUTO-28-F3 — escalation audit log + traceability
- US-AUTO-28-F4 — escalation replay protection

## Iteration Notes
- F1 focuses strictly on validation contract
- integrity and audit intentionally separated for atomicity

---

=== FILE: 06_manual_actions.md ===
# Manual Actions

## Required Human Actions
materialize_story_bundle.sh US-AUTO-28-F1
validate_story_bundle.sh US-AUTO-28-F1

git checkout -b feat/us-auto-28-f1-escalation-validation
git add .
git commit -m "fix(us-auto): enforce strict escalation validation (fail-closed)"
git pushup
gh pr create --fill

run_story.sh US-AUTO-28-F1
analyze_story_run.sh US-AUTO-28-F1

## Completion Status
- Pending implementation
