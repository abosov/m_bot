
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

