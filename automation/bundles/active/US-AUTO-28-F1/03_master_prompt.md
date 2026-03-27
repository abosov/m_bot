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

