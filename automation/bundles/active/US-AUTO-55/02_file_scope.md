# File Scope

## Files Allowed To Change
- automation/bundle_packs/US-AUTO-55.bundle.md
- automation/bundles/active/US-AUTO-55/00_story.md
- automation/bundles/active/US-AUTO-55/01_context_bundle.md
- automation/bundles/active/US-AUTO-55/02_file_scope.md
- automation/bundles/active/US-AUTO-55/03_master_prompt.md
- automation/bundles/active/US-AUTO-55/04_review_checklist.md
- automation/bundles/active/US-AUTO-55/05_followups.md
- automation/bundles/active/US-AUTO-55/06_manual_actions.md
- docs/90_codex/epics/US-AUTO_REGISTRY.md
- automation/scripts/ai_review_story_run.sh
- automation/scripts/classify_review_story_run.sh
- automation/scripts/review_gate_story_run.sh
- automation/scripts/analyze_story_run.sh
- tests/test_ai_review_story_run.py
- tests/test_classify_review_story_run.py
- tests/test_review_gate_story_run.py
- tests/test_analyze_story_run.py
- tests/test_review_pipeline_validation_contract.py

## Files Not Allowed To Change
- automation/scripts/run_story.sh
- automation/scripts/review_story_run.sh
- automation/run_codex_task.sh
- automation/scripts/commit_story_artifacts.sh
- automation/scripts/materialize_story_bundle.sh
- automation/scripts/validate_story_bundle.sh
- tests/test_run_story.py
- tests/test_run_codex_task.py
- any files outside the defined scope

## Scope Notes
Allowed change types:
- narrow downstream evidence/compliance logic
- deterministic reject reasoning
- focused test updates

Hard limits:
- no orchestration changes
- no diff fidelity changes
- no UX expansion (US-AUTO-56)

