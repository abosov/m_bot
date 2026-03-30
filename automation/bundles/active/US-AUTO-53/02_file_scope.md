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
- any tests unrelated to run diff, analyze messaging, or review gate fidelity

## Scope Notes

Allowed change types:
- deterministic diff generation and comparison fixes
- narrow fail-closed analysis messaging updates, if required
- focused regression tests for the exact committed-HEAD mismatch contract
- conservative registry update to register US-AUTO-53 and adjust next recommended ordering

Forbidden change types:
- escalation feature changes
- orchestration redesign
- manual-finish UX expansion
- broad refactors
- weakening stale-evidence rejection
- changing external test contracts to hide the defect

Hard anti-drift rule:
If the solution appears to require changes outside the allowed file list, stop and record a follow-up instead of widening this story.

