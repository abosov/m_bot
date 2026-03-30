## Role

You are the implementation engineer for the US-AUTO automation pipeline. Work only within the narrow review-artifact fidelity boundary defined for US-AUTO-53.

## Goal

Fix the committed-HEAD `diff.patch` fidelity defect so downstream review compares the exact committed implementation delta represented by the pinned run, without weakening any fail-closed review safeguards.

## Source of Truth

- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/run_codex_task.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/run_story.sh`
- `tests/test_run_codex_task.py`
- `tests/test_review_gate_story_run.py`
- `tests/test_analyze_story_run.py`

## Files Allowed To Change

- `automation/run_codex_task.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `tests/test_run_codex_task.py`
- `tests/test_review_gate_story_run.py`
- `tests/test_analyze_story_run.py`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Files Not Allowed To Change

- `automation/scripts/run_story.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/commit_story_artifacts.sh`
- `automation/bundle_packs/US-AUTO-28-F1.bundle.md`
- `automation/bundles/active/US-AUTO-28-F1/**`
- any application or runtime files outside the automation review boundary
- any unrelated tests

## Atomic Task Isolation Contract

Implement exactly one thing: deterministic committed-HEAD `diff.patch` fidelity for downstream review.

Do not:
- redesign manual-finish flow
- change escalation semantics
- add cache, retry, or orchestration features
- weaken fail-closed gate behavior
- broaden scope to unrelated review artifacts

If the defect cannot be fixed within the allowed files and this narrow boundary, stop and document a focused follow-up instead of widening the story.

## Execution Gate

Before changing code:
1. inspect the current committed behavior in the allowed files only
2. confirm the defect is specifically about committed-HEAD diff comparison, not stale workspace-only divergence
3. keep the external contract strict: true mismatches must still reject

During implementation:
- preserve committed-HEAD boundary semantics from US-AUTO-46
- preserve strict continuation semantics from US-AUTO-52
- preserve story-artifact filtering behavior already established downstream of US-AUTO-49 and US-AUTO-50 unless the exact committed diff target must be normalized further

## Implementation Requirements

- make the gate compare against the exact committed implementation diff intended by the pinned run
- ensure normalization is deterministic if formatting drift or target-selection drift exists
- keep stale or cross-commit evidence fail-closed
- update analyze messaging only if needed to explain the exact reject reason more precisely
- add focused regression tests that prove:
  - committed-match case passes the fidelity check
  - true mismatch still rejects
  - no scope widening into unrelated pipeline stages

## Verification Requirements

Run only the minimal relevant verification needed for this story:
- targeted tests for `run_codex_task`
- targeted tests for `review_gate_story_run`
- targeted tests for `analyze_story_run` if messaging changes
- any story-local automation checks needed to validate committed-HEAD diff fidelity

Do not claim success unless focused verification demonstrates both:
- exact committed-match acceptance
- true mismatch rejection

## Output

Produce:
- minimal code changes within allowed files
- focused regression tests
- conservative registry update for US-AUTO-53
- no unrelated edits

If blocked, report the exact narrow blocker and stop without workaround.

