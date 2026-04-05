# Story Bundle Pack

Story-ID: US-AUTO-72
Version: 2

---

=== FILE: 00_story.md ===

## Story ID and Title

US-AUTO-72 — Clean delivery via diff isolation for valid committed-head implementations

## Objective

Guarantee that a valid committed-head implementation can reach success boundary when Codex produces contamination limited to explicitly supported companion artifacts, without weakening the existing fail-closed scope contract for real out-of-scope changes.

## Scope

This story is contract-level but implemented within a **single delivery slice**:

* automation/scripts/run_story.sh
* automation/run_codex_task.sh
* their direct contract tests

Included:

* detection of contaminated diff (mixed in-scope + out-of-scope changes)
* isolation of allowed-scope changes
* delivery using only the valid subset
* generation of:

  * review_bundle.md
  * chatgpt_review_prompt.md

Excluded:

* modifications to:

  * analyze
  * classify
  * review_gate
* expansion of allowed file scope
* modification of prior story bundle artifacts (US-AUTO-70, US-AUTO-71)

## Non-goals

* forcing Codex to produce clean diffs
* modifying review pipeline stages
* relaxing fail-closed behavior globally

## Dependencies

* US-AUTO-71 (valid implementation exists)
* existing scope validation contract

## Source of Truth

* run_story.sh
* run_codex_task.sh
* diff.patch produced by Codex runs
* scope definition in 02_file_scope.md

## Current Code Reality

Codex may produce mixed change sets that contain:

* valid in-scope implementation changes
* explicitly known companion contamination
* real out-of-scope changes

The existing pipeline already has a fail-closed scope contract: real out-of-scope changes must block execution before pytest.

The actual gap for this story is narrower:
* explicitly supported companion contamination can poison delivery artifacts or review surface even when the real implementation is valid
* the fix must isolate only that known contamination
* the fix must NOT redefine real out-of-scope changes as ignorable

## Target Outcome

Pipeline must:

* isolate only explicitly supported companion contamination from delivery and review artifacts
* preserve valid in-scope implementation changes
* continue to fail closed on real out-of-scope changes
* reach success boundary when the only contamination is from explicitly supported companion artifacts

Invariants:

* valid implementation + explicit companion contamination → deliver using the valid implementation surface
* any real out-of-scope change remains a blocking error before pytest
* no generic "filter down to allowed scope" behavior is permitted

## Atomic Task Isolation Contract

Strict boundary:

Allowed changes:

* run_story.sh
* run_codex_task.sh
* tests/test_run_story.py
* tests/test_run_codex_task.py

Forbidden:

* analyze_story_run.sh
* classify_review_story_run.sh
* review_gate_story_run.sh
* any bundle artifacts outside US-AUTO-72

## Risks

* accidentally converting fail-closed scope validation into fail-open filtering
* masking real out-of-scope changes by dropping them from worktree change lists
* rewriting tests to accept filtered-empty behavior instead of preserving the real contract
* breaking deterministic review evidence by changing the meaning of changed_files.txt

## Manual Actions

* materialize bundle
* validate bundle
* run story
* analyze new run

## Acceptance Notes

Success when:

* explicit companion contamination no longer blocks delivery of a valid in-scope implementation
* review_bundle.md generated
* chatgpt_review_prompt.md generated
* no out-of-scope files are applied to repo
* real out-of-scope changes still fail before pytest
* tests continue to enforce the existing scope-guard contract rather than redefining it

---

=== FILE: 01_context_bundle.md ===

## Source of Truth

run_story.sh
run_codex_task.sh

## Current Code Reality

Codex produces superset diffs.
Pipeline expects exact-scope diffs.
Mismatch causes systemic failure.

## Architectural Intent

System must be robust to generator noise without weakening scope enforcement.

Key rules:

* pipeline trusts scope, not generator
* explicit companion contamination may be isolated
* real out-of-scope changes must still block execution
* delivery isolation must not become a generic pre-scope filtering layer

## Risks

* silent acceptance of invalid changes
* incomplete subset extraction

## Acceptance Notes

Must prove:

* explicit companion contamination is isolated correctly
* real out-of-scope changes are still rejected
* no generic filtering of arbitrary changed paths is introduced

---

=== FILE: 02_file_scope.md ===

## Files Allowed To Change

automation/scripts/run_story.sh
automation/run_codex_task.sh
tests/test_run_story.py
tests/test_run_codex_task.py

## Files Not Allowed To Change

automation/scripts/analyze_story_run.sh
automation/scripts/classify_review_story_run.sh
automation/scripts/review_gate_story_run.sh
tests/test_analyze_story_run.py
tests/test_classify_review_story_run.py
tests/test_review_gate_story_run.py
tests/test_review_pipeline_validation_contract.py

automation/bundle_packs/US-AUTO-70.bundle.md
automation/bundle_packs/US-AUTO-71.bundle.md

## Scope Notes

Delivery isolation must happen inside the pipeline, not via Codex discipline.

Hard scope rules for this story:

* allowed behavior:
  * isolate only explicitly supported companion contamination
  * preserve valid in-scope implementation changes
  * keep the existing fail-closed scope contract

* forbidden behavior:
  * filtering arbitrary tracked or untracked worktree changes down to the allowed file list before normal scope validation
  * redefining real out-of-scope changes as ignorable noise
  * changing tests to accept fail-open filtered-empty semantics

---

=== FILE: 03_master_prompt.md ===

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

=== FILE: 04_review_checklist.md ===

## Scope Validation

Reject if ANY forbidden file changed.

## Functional Validation

Approve only if:

* explicit companion isolation is implemented
* contaminated diff no longer blocks delivery only in the explicit companion case
* real out-of-scope changes still block before pytest
* success boundary is reachable without weakening fail-closed scope enforcement

## Verification

Tests must:

* simulate explicit companion contamination
* simulate real out-of-scope violations
* assert delivery succeeds only for the explicit companion case
* assert real scope violations still fail

---

=== FILE: 05_followups.md ===

## Follow-Up Prompt Queue

NO further split allowed.

## Iteration Notes

This story resolves entire split chain.

---

=== FILE: 06_manual_actions.md ===

## Required Human Actions

1. Save bundle
2. materialize
3. validate
4. commit
5. run_story
6. analyze

## Completion Status

Pending implementation
