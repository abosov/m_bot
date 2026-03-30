## Story ID and Title

**Story ID:** US-AUTO-53  
**Title:** Committed-HEAD diff.patch review fidelity

## Objective

Restore a strict fail-closed review artifact fidelity contract so `review_gate_story_run.sh` does not reject a clean committed-HEAD run with `review_diff_patch_mismatch` when the pinned run evidence was generated from the same committed implementation state.

## Scope

This story is limited to the review-artifact fidelity boundary for `diff.patch` on committed HEAD.

In scope:
- deterministic generation and comparison of `diff.patch` for downstream review on committed HEAD
- normalization rules required to keep the diff comparison stable
- focused regression coverage for committed-HEAD diff fidelity
- conservative run-analysis messaging if needed to preserve the fail-closed contract
- conservative registry update for US-AUTO-53

## Non-goals

- no changes to escalation policy semantics
- no changes to escalation artifact schema beyond what already exists
- no weakening of review gate strictness
- no manual-finish UX redesign
- no retry orchestration, caching, or reuse expansion
- no broad changes across unrelated pipeline stages
- no test contract rewrites to mask the defect

## Dependencies

- US-AUTO-45 — deterministic review gate artifact reuse
- US-AUTO-46 — review operates strictly on committed HEAD
- US-AUTO-49 — scope validation ignores committed active-story bundle artifacts
- US-AUTO-50 — AI review structured output and review artifact fidelity stabilization
- US-AUTO-52 — strict manual-finish continuation contract

## Source of Truth

- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/run_codex_task.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/run_story.sh`
- `tests/test_run_codex_task.py`
- `tests/test_review_gate_story_run.py`
- `tests/test_analyze_story_run.py`

## Current Code Reality

`US-AUTO-28-F1` was resumed on a clean branch from `origin/main`, passed story-local tests on committed HEAD, and successfully produced fresh run, analyze, and AI review evidence on clean committed state. Despite that, `review_gate_story_run.sh` still rejected the pinned run with `review_diff_patch_mismatch`, even though committed HEAD consistency matched.

That narrows the remaining blocker to downstream review-artifact fidelity around `diff.patch` comparison on committed HEAD.

## Target Outcome

After this story:
- a clean committed-HEAD rerun produces a `diff.patch` artifact that remains valid for downstream gate comparison against the same committed implementation state
- `review_gate_story_run.sh` rejects only true mismatches, not formatting drift or wrong-target comparison
- the review pipeline remains fail-closed for stale, mismatched, or cross-commit evidence
- `US-AUTO-28-F1` can be resumed only after this follow-up is merged

## Atomic Task Isolation Contract

This story must solve exactly one problem: committed-HEAD `diff.patch` fidelity at the review boundary.

Allowed:
- fix the generation and comparison contract for review diff evidence
- add narrow regression coverage for the exact mismatch class
- update analysis messaging only when necessary to preserve the same strict boundary

Forbidden:
- broad manual-finish workflow redesign
- operator UX expansion
- escalation-policy changes
- cache, reuse, or retry features
- scope widening into unrelated review artifacts or orchestration layers

If implementation pressure expands beyond committed-HEAD diff fidelity, stop and split a follow-up story instead of widening this one.

## Risks

- accidentally weakening the gate so true stale evidence passes
- fixing the symptom in tests while leaving runtime behavior inconsistent
- scope drift into generic manual-finish or review recovery UX

## Manual Actions

- materialize the bundle pack into active bundle files
- validate the bundle before any code changes
- update the registry conservatively to add US-AUTO-53 and make it the next recommended story
- create a dedicated feature branch before running automation
- commit story artifacts before `run_story.sh`
- after implementation commit, rerun the story and analyze the fresh run directory
- do not reuse any pinned `AUTOMATION_RUN_DIR` after a new commit

## Acceptance Notes

Acceptance requires all of the following:
- committed-HEAD review diff fidelity is deterministic
- true stale or mismatched diff evidence still fails closed
- focused tests cover the exact mismatch and non-mismatch cases
- the story remains narrow and does not redesign manual-finish workflow
- downstream evidence remains consistent with the invariant `run -> commit -> rerun -> review`
- `US-AUTO-28-F1` remains blocked until this follow-up is merged, then becomes resumable

