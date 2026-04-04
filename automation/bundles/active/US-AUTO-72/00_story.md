
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

