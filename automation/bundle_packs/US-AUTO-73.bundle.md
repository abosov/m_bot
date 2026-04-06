# Story Bundle Pack

Story-ID: US-AUTO-73
Version: 1

=== FILE: 00_story.md ===

## Story ID and Title

US-AUTO-73 — Refine companion-filter semantics

## Objective

Replace the current coarse companion-filter enablement heuristic with path-semantic filtering so review-surface computation and downstream review contracts remain correct for mixed-scope stories.

This story is a contract-level governance and enforcement story focused on the execution/review-surface layer and the downstream consumers that must reuse the same semantic filtering contract.

## Scope

Implement a single source of truth for identifying non-runtime companion artifacts by path semantics rather than by story-level code-only classification.

Allowed scope in this story:

* remove dependence on `story_is_code_only_for_execution_filter` for companion filtering decisions
* introduce a shared path-semantic helper for non-runtime companion artifacts
* update review-surface producers/consumers that currently depend on the coarse heuristic
* update tests to cover code-only, mixed-scope, and docs-only/path-semantic cases
* document the new contract in the registry as part of story completion

Pipeline layer:

* run
* review surface computation
* downstream review/analyze/classify/gate consumers of filtered artifacts

## Non-goals

* no change to manual-finish workflow semantics
* no change to rerun convergence policy
* no broad UX/operator-message redesign
* no review decision override mechanism changes
* no unrelated refactor of bundle materialization/validation
* no change to unrelated registry entries beyond status/progress and the semantic-filter contract note for this story

## Dependencies

* US-AUTO-70 must be implemented and merged
* pinned-artifact review/gate consistency already exists and must be preserved
* current active registry and bundle validator contract remain source of truth for story packaging

## Source of Truth

* `docs/90_codex/epics/US-AUTO_REGISTRY.md`
* `automation/run_codex_task.sh`
* `automation/scripts/run_story.sh`
* `automation/scripts/analyze_story_run.sh`
* `automation/scripts/review_story_run.sh`
* `automation/scripts/ai_review_story_run.sh`
* `automation/scripts/classify_review_story_run.sh`
* `automation/scripts/review_gate_story_run.sh`
* existing tests covering review surface, changed files, and companion artifact filtering behavior

## Current Code Reality

Current behavior uses a coarse story-level heuristic equivalent to:

* code-only story -> companion filter enabled
* mixed-scope story -> companion filter disabled

That model is incorrect because companion filtering is actually about the semantic role of specific paths, not whether the whole story is code-only. As a result, mixed-scope stories can surface false-negative review outcomes, unnecessary rejects, and decision-override situations even when the changed files are semantically safe to exclude from runtime/review surface calculations.

The filtering logic is also effectively duplicated across multiple pipeline stages, increasing drift risk.

## Target Outcome

The pipeline must classify paths by semantic role and exclude only non-runtime companion artifacts from review-surface computation regardless of whether the story is code-only or mixed-scope.

Required outcome:

* companion filtering is path-semantic, not story-type based
* mixed-scope stories remain eligible for correct filtering
* docs-only non-runtime companion artifacts are excluded from runtime/review surface where appropriate
* runtime-critical and companion-operational files that affect execution or source-of-truth behavior remain included
* all downstream consumers reuse the same contract without drift
* review outcomes become deterministic without relying on decision override for this defect class

## Atomic Task Isolation Contract

This story is contract-level by design because the defect spans one contract across multiple pipeline consumers, but it remains a single problem with one responsibility boundary:

* define and enforce semantic companion-filter classification

Hard boundaries:

* do not mix in unrelated retry, manual-finish, or UI/operator ergonomics changes
* do not change external contracts unless required to align them to the new semantic filtering rule
* do not introduce separate fallback heuristics
* do not keep both old and new filtering models active in parallel

Fail closed:

* if a path cannot be safely classified as non-runtime companion artifact, treat it as included in runtime/review surface
* no permissive fallback to story-level code-only shortcuts

## Risks

* regression in changed-files and diff.patch fidelity
* drift if one downstream stage continues to use the legacy heuristic
* accidental over-exclusion of files that are operationally significant
* accidental under-exclusion of non-runtime companion docs causing noisy surfaces

## Manual Actions

* materialize the bundle pack for US-AUTO-73
* validate the active bundle
* update the registry status for US-AUTO-73 before implementation begins
* create a dedicated feature branch before running automation
* commit bundle artifacts before `run_story.sh`
* after implementation and merge, update the registry status to Implemented and record the semantic-filter contract

## Acceptance Notes

Acceptance requires all of the following:

* the implementation no longer depends on `story_is_code_only_for_execution_filter` for companion filtering
* a single semantic path helper exists and is reused everywhere companion filtering decisions are made
* mixed-scope stories with non-runtime docs do not incorrectly disable filtering
* docs-only non-runtime artifacts do not pollute runtime/review surface
* runtime-critical changes are always retained in the surface
* downstream scripts remain consistent on the same pinned artifacts
* tests explicitly cover mixed-scope and docs-only semantic cases
* registry workflow notes reflect that story completion must update status and record the new contract

=== FILE: 01_context_bundle.md ===

## Source of Truth

* `docs/90_codex/epics/US-AUTO_REGISTRY.md`
* `automation/run_codex_task.sh`
* `automation/scripts/run_story.sh`
* `automation/scripts/analyze_story_run.sh`
* `automation/scripts/review_story_run.sh`
* `automation/scripts/ai_review_story_run.sh`
* `automation/scripts/classify_review_story_run.sh`
* `automation/scripts/review_gate_story_run.sh`
* relevant tests under `tests/`

## Current Code Reality

US-AUTO-70 resolved rerun-preflight and review-surface recomputation correctness, but it exposed that companion filtering still relies on a story-level heuristic that is too coarse. The practical defect is not about whether a story is mixed or code-only; it is about whether specific changed paths are non-runtime companion artifacts.

Current risk areas:

* false rejects when mixed-scope stories include harmless docs/registry changes
* duplicated classification behavior across scripts
* inconsistency between changed_files, diff.patch, and review-surface consumers if the same semantic rule is not reused everywhere

## Architectural Intent

The architectural intent is a single fail-closed semantic contract:

* classify each changed path by semantic role
* exclude only non-runtime companion artifacts
* preserve runtime-critical and operationally significant files
* keep producers and consumers of review artifacts aligned on the same filtered view

This story should reduce the need for manual override and prevent recurrence of the same false-negative class seen after US-AUTO-70.

## Risks

* hidden coupling between scripts may cause one consumer to lag behind the new contract
* tests may currently encode old code-only assumptions and need precise correction
* registry/source-of-truth docs used operationally must not be wrongly excluded if they influence execution or validation behavior

## Acceptance Notes

Reviewer should verify:

* no lingering story-level code-only heuristic controls companion filtering
* semantic helper is used consistently in all relevant scripts
* mixed-scope correctness is demonstrated by tests
* docs-only non-runtime artifacts are filtered out only where contractually intended
* no unrelated pipeline behavior is changed

=== FILE: 02_file_scope.md ===

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
* bundle validator contract files unrelated to this story
* unrelated application/runtime product code outside automation pipeline
* GitHub workflow files
* secrets, environment configuration, or deployment scripts
* any active story bundle artifacts other than US-AUTO-73 bundle pack/materialized files created through the normal workflow

## Scope Notes

Allowed change types:

* add or refactor a shared semantic helper for non-runtime companion artifact classification
* replace old heuristic checks with the shared helper
* align tests to the new contract
* update registry story status/notes for this story

Forbidden change types:

* broad refactors unrelated to companion filtering
* operator UX rewrites
* retry/manual-finish semantics changes
* introducing alternate fallback heuristics
* editing materialized active bundle files by hand instead of through the bundle workflow

=== FILE: 03_master_prompt.md ===

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

=== FILE: 04_review_checklist.md ===

## Scope Validation

HARD BLOCK if any changed file is outside the allowed scope.

HARD BLOCK if the implementation changes:

* manual-finish semantics
* rerun convergence semantics
* bundle validator/materializer logic
* unrelated operator UX behavior

HARD BLOCK if old story-level code-only gating remains a controlling factor for companion filtering.

## Functional Validation

Review must confirm all of the following:

* a semantic non-runtime companion artifact classifier exists
* filtering is path-semantic, not story-type based
* mixed-scope stories can still receive correct filtering
* docs-only non-runtime artifacts are excluded only where intended
* runtime-critical paths remain included
* all relevant downstream stages use the same contract and do not drift

Reject if any consumer still computes a different filtered surface from the others.

## Verification

Require targeted automated tests covering:

* mixed-scope + non-runtime docs case
* docs-only non-runtime artifact case
* runtime-critical path inclusion case
* cross-stage consistency for filtered changed files / diff.patch / review inputs where applicable

Binary outcome only:

* APPROVE if all scope, functional, and verification checks pass
* REJECT otherwise

=== FILE: 05_followups.md ===

## Follow-Up Prompt Queue

No planned follow-up is required if US-AUTO-73 fully replaces the old heuristic and aligns all relevant consumers on the shared semantic contract.

If implementation uncovers a separate unrelated issue, do not expand this story. Record it in the registry as a distinct future story only after US-AUTO-73 is completed.

## Iteration Notes

This story is intentionally elevated to contract level to prevent another micro-split in the same defect chain. The implementation must finish the semantic-filter correction end-to-end within the defined boundary rather than spawning another heuristic-related continuation.

=== FILE: 06_manual_actions.md ===

## Required Human Actions

1. Save this bundle pack to `automation/bundle_packs/US-AUTO-73.bundle.md`.
2. Run `automation/scripts/materialize_story_bundle.sh US-AUTO-73`.
3. Run `automation/scripts/validate_story_bundle.sh US-AUTO-73`.
4. Update the registry through the bundle-driven workflow so US-AUTO-73 is marked ready/in progress as appropriate.
5. Create a feature branch for US-AUTO-73 before implementation.
6. Commit bundle artifacts on that branch.
7. Run `automation/scripts/run_story.sh US-AUTO-73`.
8. Run `automation/scripts/analyze_story_run.sh US-AUTO-73` against the latest run after implementation.
9. After merge, update the registry status to Implemented and record the semantic companion-filter contract as completed.

## Completion Status

Bundle prepared for materialize + validate.
