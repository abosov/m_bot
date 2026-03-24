# File Scope

## Files Allowed To Change
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/run_story.sh`
- `automation/scripts/escalate_story.sh`
- `tests/test_review_gate_story_run.py`
- `tests/test_analyze_story_run.py`
- `tests/test_run_story.py`
- `tests/test_escalate_story.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/US-AUTO-28.bundle.md`
- `automation/bundles/active/US-AUTO-28/00_story.md`
- `automation/bundles/active/US-AUTO-28/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-28/02_file_scope.md`
- `automation/bundles/active/US-AUTO-28/03_master_prompt.md`
- `automation/bundles/active/US-AUTO-28/04_review_checklist.md`
- `automation/bundles/active/US-AUTO-28/05_followups.md`
- `automation/bundles/active/US-AUTO-28/06_manual_actions.md`

## Files Not Allowed To Change
- database migrations
- application product code outside automation governance flow
- GitHub Actions workflows unless a direct blocker is proven
- unrelated bundle packs or active bundles for other stories
- unrelated review classification taxonomy files unless directly required by this story
- any file not needed for the escalation gate contract

