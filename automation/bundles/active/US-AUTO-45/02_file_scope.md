# US-AUTO-45: File Scope

## Files Allowed To Change
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `tests/test_review_gate_story_run.py`
- `tests/test_analyze_story_run.py`
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/US-AUTO-45.bundle.md`
- `automation/bundles/active/US-AUTO-45/00_story.md`
- `automation/bundles/active/US-AUTO-45/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-45/02_file_scope.md`
- `automation/bundles/active/US-AUTO-45/03_master_prompt.md`
- `automation/bundles/active/US-AUTO-45/04_review_checklist.md`
- `automation/bundles/active/US-AUTO-45/05_followups.md`
- `automation/bundles/active/US-AUTO-45/06_manual_actions.md`

## Files Not Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/scripts/commit_story_artifacts.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/build_bundle_pack.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/run_codex_task.sh`
- `automation/scripts/check_allowed_files.sh`
- `automation/scripts/merge_recommendation_contract.sh`
- `automation/bundle_packs/US-AUTO-46.bundle.md`

## Scope Notes
- The issue to solve is deterministic reuse at gate time, not upstream run or materialization behavior.
- AI review and classification producers should remain unchanged; this story constrains gate as consumer.
- Reverse sync and bundle-pack tooling are explicitly deferred to US-AUTO-46.
- If tests reveal that gate determinism cannot be fixed without changing upstream producers, stop and record a follow-up instead of broadening scope.

