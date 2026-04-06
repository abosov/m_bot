
## Role

You are the implementation engineer for US-AUTO-73 working inside the Codex automation pipeline with strict fail-closed governance.

## Goal

Implement semantic companion-filter classification so review-surface computation excludes only non-runtime companion artifacts by path semantics and does not depend on story-level code-only classification.

## Source of Truth

* `docs/90_codex/epics/US-AUTO_REGISTRY.md`
* `automation/run_codex_task.sh`
* `automation/scripts/run_story.sh`
* `automation/scripts/analyze_story_run.sh`
* `automation/scripts/review_story_run.sh`
* `automation/scripts/ai_review_story_run.sh`
* `automation/scripts/classify_review_story_run.sh`
* `automation/scripts/review_gate_story_run.sh`
* tests under `tests/` for the listed scripts

## Files Allowed To Change

* `automation/run_codex_task.sh`
* `automation/scripts/run_story.sh`
* `automation/scripts/analyze_story_run.sh`
* `automation/scripts/review_story_run.sh`
* `automation/scripts/ai_review_story_run.sh`
* `automation/scripts/classify_review_story_run.sh`
* `automation/scripts/review_gate_story_run.sh`
* `tests/test_run_codex_task.py`
* `tests/test_run_story.py`
* `tests/test_analyze_story_run.py`
* `tests/test_review_story_run.py`
* `tests/test_ai_review_story_run.py`
* `tests/test_classify_review_story_run.py`
* `tests/test_review_gate_story_run.py`
* `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Files Not Allowed To Change

* `automation/scripts/materialize_story_bundle.sh`
* `automation/scripts/validate_story_bundle.sh`
* unrelated workflow or deployment files
* application code outside the automation pipeline
* any bundle files except through normal story bundle workflow outputs

## Atomic Task Isolation Contract

This is a single contract-level task focused only on semantic companion filtering.

Hard stop rules:

* do not change manual-finish logic
* do not change rerun convergence logic
* do not change unrelated review message wording unless required by contract correctness
* do not retain old `story_is_code_only_for_execution_filter` behavior as a fallback for companion filtering
* do not expand scope into optimization or UX improvements

Fail closed:

* when uncertain, keep a path included in runtime/review surface
* do not exclude a path unless the helper can classify it as non-runtime companion artifact under the contract

## Execution Gate

Before coding:

* inspect all current uses of companion-filter or code-only execution-filter logic in allowed files
* identify a single shared classification rule and ensure all listed scripts consume it consistently
* preserve pinned-artifact determinism and review-surface fidelity
* keep changes small and contract-driven

## Implementation Requirements

* remove companion-filter dependence on `story_is_code_only_for_execution_filter`
* introduce or centralize a helper equivalent to `is_non_runtime_companion_artifact_path()`
* ensure the helper classifies by path semantics, not by story type
* preserve inclusion of runtime-critical files such as automation execution scripts and tests
* preserve inclusion of operational source-of-truth files when they affect execution or validation behavior
* exclude only non-runtime companion artifacts
* update all relevant consumers so changed_files, diff.patch, review bundle inputs, analyze/classify/gate views, and related filtering remain aligned
* update tests for:

  * mixed-scope story with non-runtime docs does not disable filtering
  * docs-only non-runtime artifacts do not appear in runtime/review surface where excluded by contract
  * runtime-critical paths always remain included

## Verification Requirements

Run the narrowest relevant verification for touched files, including targeted pytest coverage for all updated script contracts. Verify there is no remaining reference path where the old heuristic controls companion filtering behavior.

Also verify registry updates reflect:

* US-AUTO-73 progress/state
* semantic-filter contract note
* completion-status discipline after merge

## Output

Produce:

* minimal implementation across allowed files
* targeted tests proving the new contract
* registry update for US-AUTO-73
* no unrelated edits

