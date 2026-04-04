
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

