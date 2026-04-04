
## Role

You are implementing a contract-level delivery fix for a noisy generator system.

## Goal

Ensure pipeline can:

* accept contaminated diffs
* extract allowed-scope subset
* deliver only valid changes

## Source of Truth

run_story.sh
run_codex_task.sh

## Files Allowed To Change

automation/scripts/run_story.sh
automation/run_codex_task.sh
tests/test_run_story.py
tests/test_run_codex_task.py

## Files Not Allowed To Change

ALL other files

## Atomic Task Isolation Contract

Hard rule:

Do NOT:

* modify analyze/classify/gate
* expand scope
* rely on Codex producing clean diffs

## Execution Gate

If solution requires:

* touching forbidden files
  → STOP and fail

## Implementation Requirements

Implement:

1. Diff filtering step:

   * parse changed files
   * keep only allowed paths

2. Patch application:

   * apply only filtered subset

3. Validation:

   * if subset empty → fail
   * else proceed

4. Ensure:

   * no out-of-scope file is applied

## Verification Requirements

Tests must confirm:

* contaminated diff still succeeds
* invalid files are ignored
* fail if only invalid files present

## Output

Modify only allowed files.

---

