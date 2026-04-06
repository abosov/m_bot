
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

