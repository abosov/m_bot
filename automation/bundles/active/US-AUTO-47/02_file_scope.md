# File Scope

## Files Allowed To Change
- automation/scripts/run_story.sh
- automation/scripts/analyze_story_run.sh
- tests/test_run_story.py
- tests/test_analyze_story_run.py
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md
- docs/90_codex/CODEX_OPERATING_SYSTEM.md
- automation/bundles/active/US-AUTO-47/**
- automation/bundle_packs/US-AUTO-47.bundle.md

## Files Not Allowed To Change
- automation/run_codex_task.sh
- automation/scripts/review_gate_story_run.sh
- automation/scripts/ai_review_story_run.sh
- automation/scripts/classify_review_story_run.sh

## Scope Notes
Allowed:
- detection logic
- boundary classification
- messaging
- tests

Forbidden:
- runner redesign
- retry logic
- orchestration

