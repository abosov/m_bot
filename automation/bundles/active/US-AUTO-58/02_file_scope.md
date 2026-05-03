## Files Allowed To Change

Runtime scripts:

    automation/scripts/analyze_story_run.sh
    automation/scripts/run_story.sh
    automation/scripts/refresh_review_evidence.sh
    automation/scripts/story_stage_loop.sh
    automation/scripts/ai_review_story_run.sh
    automation/scripts/review_story_run.sh
    automation/scripts/classify_review_story_run.sh
    automation/scripts/review_gate_story_run.sh

Test files:

    tests/test_analyze_story_run.py
    tests/test_run_story.py
    tests/test_refresh_review_evidence.py
    tests/test_ai_review_story_run.py
    tests/test_review_story_run.py
    tests/test_classify_review_story_run.py
    tests/test_review_classification_script.py
    tests/test_review_gate_story_run.py
    tests/test_review_pipeline_validation_contract.py

Documentation:

    docs/90_codex/US_AUTO_OPERATOR_GUIDE.md
    docs/90_codex/epics/US-AUTO_REGISTRY.md

Story artifacts:

    automation/bundle_packs/US-AUTO-58.bundle.md
    automation/bundles/active/US-AUTO-58/00_story.md
    automation/bundles/active/US-AUTO-58/01_context_bundle.md
    automation/bundles/active/US-AUTO-58/02_file_scope.md
    automation/bundles/active/US-AUTO-58/03_master_prompt.md
    automation/bundles/active/US-AUTO-58/04_review_checklist.md
    automation/bundles/activ-AUTO-58/05_followups.md
    automation/bundles/active/US-AUTO-58/06_manual_actions.md

Optional new helper files, only if justified by existing project structure:

    automation/scripts/story_stage_loop.sh
    automation/scripts/lib/*
    tests/test_*loop*.py

## Files Not Allowed To Change

Do not modify unrelated business feature code.

Do not modify application runtime unrelated to the US-AUTO automation pipeline.

Do not modify production bot behavior.

Do not modify secrets, environment files, generated caches, or local-only artifacts.

Do not commit:

    tests/__pycache__/*
    .pytest_cache/*
    automation/runs/*
    automation/story_change_ledger.jsonl unless intentionally required and reviewed

## Scope Boundaries

This story may add loop-cap logic and tests.

This story may update operator documentation.

This story may clarify the US-AUTO-58 registry row while keeping the story Planned during implementation.

This story must not close US-AUTO-58 in the registry until the implementation PR has been merged and a separate registry closeout step is performed.

This story must not implement:

    - full deterministic orchestration;
    - automatic end-to-end stage advancement;
    - full decision packet UX;
    - broad refactors of all scripts;
    - changes to external review contracts unless explicitly required and tested.

## Review Notes

Review must verify that the implementation does not reintroduce the accepted-implementation rerun loop.

Review must verify that the no-Codex refresh path remains valid.

Review must verify that the loop cap stops repeated non-converging stage churn without blocking first-pass normal correction.

Review must verify that dirty tree and stale evidence safety checks remain stricter than convenience.

