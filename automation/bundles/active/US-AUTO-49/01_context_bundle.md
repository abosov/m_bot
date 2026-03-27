# Context Bundle — US-AUTO-49

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- runtime orchestration scripts and their tests

## Current Code Reality
Recent execution of `US-AUTO-28-F1` reproduced a workflow blocker before review stage:
- Codex produced useful in-scope implementation edits
- scope validation also counted already-committed bundle artifacts for the active story
- the run failed even though the story logic itself was not the problem

The defect is not inside `US-AUTO-28-F1`. It is an orchestration contract gap between:
- committed story artifacts required before run, and
- runtime scope validation that should assess only the Codex-produced implementation delta

## Architectural Intent
The pipeline should preserve both of these invariants simultaneously:
1. active-story bundle artifacts must be committed before run
2. runtime scope validation must evaluate only the implementation delta created by the run

Therefore the correct fix is a narrow baseline/provenance refinement in runtime orchestration, not a relaxation of scope enforcement and not a change to bundle policy.

## Risks
- accidental scope weakening if bundle artifact ignores are not tied to the active story ID
- accidental cross-story leakage if canonical artifact paths are not enforced
- regression in change accounting if ignored files are excluded too late in the process
- temptation to “fix” this in review or registry logic instead of runtime orchestration

## Acceptance Notes
The implementation is acceptable only if:
- it ignores committed bundle artifacts for the same active story
- it keeps rejecting all true out-of-scope implementation changes
- it fails closed on ambiguous provenance
- it leaves `US-AUTO-28-F1` untouched and merely unblocks its future rerun path

