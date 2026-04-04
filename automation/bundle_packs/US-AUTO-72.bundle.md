# Story Bundle Pack

Story-ID: US-AUTO-72
Version: 2

---

=== FILE: 00_story.md ===

## Story ID and Title

US-AUTO-72 — Clean delivery via diff isolation for valid committed-head implementations

## Objective

Guarantee that a valid committed-head implementation can reach success boundary even when Codex produces a contaminated diff, by isolating and applying only the valid in-scope subset.

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

Codex produces diffs containing:

* valid changes (in allowed scope)
* unrelated changes (outside scope)

Current pipeline:

* rejects entire diff if any out-of-scope changes exist
* cannot proceed to success boundary even when valid subset exists

## Target Outcome

Pipeline must:

* detect mixed diffs
* extract only allowed-scope changes
* ignore all other changes for delivery
* proceed to success boundary using the valid subset

Invariant:

valid subset exists → deliver
no valid subset → fail closed

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

* accidentally allowing out-of-scope changes
* masking real errors instead of isolating
* breaking fail-closed guarantees

## Manual Actions

* materialize bundle
* validate bundle
* run story
* analyze new run

## Acceptance Notes

Success when:

* contaminated diff still leads to success boundary if valid subset exists
* review_bundle.md generated
* chatgpt_review_prompt.md generated
* no out-of-scope files applied to repo

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

System must be robust to generator noise.

Key rule:

Pipeline trusts scope, not generator.

## Risks

* silent acceptance of invalid changes
* incomplete subset extraction

## Acceptance Notes

Must prove:

* subset extraction works
* invalid files are excluded

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

Scope filtering must happen **inside pipeline**, not via Codex discipline.

---

=== FILE: 03_master_prompt.md ===

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

=== FILE: 04_review_checklist.md ===

## Scope Validation

Reject if ANY forbidden file changed.

## Functional Validation

Approve only if:

* subset extraction implemented
* contaminated diff no longer blocks delivery
* success boundary reachable

## Verification

Tests must:

* simulate contaminated diff
* assert only allowed subset applied

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
