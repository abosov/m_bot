## Files Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/scripts/analyze_story_run.sh`
- `tests/test_run_story.py`
- `tests/test_analyze_story_run.py`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Files Not Allowed To Change
- `automation/scripts/review_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/run_codex_task.sh`
- `automation/scripts/commit_story_artifacts.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/story_change_ledger.jsonl`
- any bundle pack or active bundle for stories other than US-AUTO-56
- any test files other than `tests/test_run_story.py` and `tests/test_analyze_story_run.py`

## Scope Notes
Allowed change types:
- add deterministic stage-gate summary text
- add explicit “allowed next step” / “forbidden next step” guidance
- add targeted tests that verify stage-gate guidance for normal and manual-finish paths
- update the registry conservatively for US-AUTO-56 lifecycle status and next-action notes

Disallowed change types:
- changing review/gate decision logic
- introducing new files or registries
- adding rerun-skip, escalation, telemetry, reuse, or verification-selection behavior
- refactoring unrelated code paths for style only
- changing external contracts outside stage-gate guidance

