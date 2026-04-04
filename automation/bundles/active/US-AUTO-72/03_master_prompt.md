
## Role

You are implementing a contract-level delivery fix for a noisy generator system.

## Goal

Ensure pipeline can isolate explicitly supported companion contamination from a valid implementation diff and still deliver the valid implementation, while preserving the existing fail-closed behavior for real out-of-scope changes.

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

Hard rules:

Do NOT:

* modify analyze/classify/gate
* expand scope
* rely on Codex producing clean diffs
* introduce any generic "filter changed paths to allowed scope" layer over arbitrary worktree changes
* redefine real out-of-scope changes as ignorable
* rewrite tests to accept fail-open filtering behavior

## Execution Gate

If solution requires:

* touching forbidden files
  → STOP and fail

## Implementation Requirements

Implement:

1. Explicit companion isolation only:

   * detect and exclude only explicitly supported companion contamination
   * do not introduce arbitrary allowed-scope filtering over all changed paths

2. Delivery preservation:

   * preserve the valid in-scope implementation surface
   * generate delivery and review artifacts from that preserved implementation surface

3. Validation:

   * if the remaining implementation surface is empty after explicit companion isolation → fail closed
   * if any real out-of-scope change exists → keep the existing blocking behavior before pytest

4. Ensure:

   * no out-of-scope file is applied
   * changed_files.txt and downstream review evidence keep their existing fail-closed meaning


## Hard Stop Rules

STOP and fail if the proposed solution does any of the following:

* filters tracked or untracked worktree changes down to the allowed file list before normal scope validation
* introduces a new pre-scope filtering layer as a substitute for real scope enforcement
* changes tests so that real out-of-scope violations are no longer blocking
* treats all contaminated diffs as deliverable merely because some allowed files exist


## Verification Requirements

Tests must confirm:

* explicit companion contamination no longer blocks valid delivery
* real out-of-scope changes still block before pytest
* fail-closed behavior remains intact when only invalid changes are present
* no generic allowed-scope filtering behavior has been introduced

## Output

Modify only allowed files.

---

