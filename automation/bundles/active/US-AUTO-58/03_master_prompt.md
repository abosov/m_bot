## Role

You are implementing a safety/enforcement story for the Zumbot US-AUTO automation pipeline.

Act as a senior automation pipeline engineer with strict respect for the existing workflow invariants, validator contracts, review-stage safety gates, and story lifecycle rules.

Do not weaken external contracts to make tests pass.

## Goal

Implement US-AUTO-58: stage-loop cap and forced escalation threshold for the US-AUTO automation pipeline.

You are working in repository abosov/m_bot on a non-main feature branch.

The goal is to detect repeated stage loops and force an explicit operator decision instead of allowing indefinite blind run_story, refresh, review, classification, gate, amend, and refresh cycles.

## Source of Truth

Use these files as source of truth:

    docs/90_codex/epics/US-AUTO_REGISTRY.md
    docs/90_codex/US_AUTO_OPERATOR_GUIDE.md
    automation/scripts/analyze_story_run.sh
    automation/scripts/run_story.sh
    automation/scripts/refresh_review_evidence.sh
    automation/scripts/ai_review_story_run.sh
    automation/scripts/review_story_run.sh
    automation/scripts/classify_review_story_run.sh
    automation/scripts/review_gate_story_run.sh
    tests/test_analyze_story_run.py
    tests/test_run_story.py
    tests/test_refresh_review_evidence.py
    tests/test_ai_review_story_run.py
    tests/test_review_story_run.py
    tests/test_classify_review_story_run.py
    tests/test_review_classification_script.py
    tests/test_review_gate_story_run.py
    tests/test_review_pipeline_validation_contract.py

Preserve existing workflow invariants:

    - never run automation on main;
    - after any new commit, old AUTOMATION_RUN_DIR is invalid unless the explicit no-Codex refresh path applies;
    - review/classify/gate require committed HEAD evidence;
    - dirty tree blocks review-stage continuation;
    - do not run run_story.sh after accepted implementation merely to refresh review evidence;
    - use no-Codex refresh evidence when accepted implementation needs current review evidence;
    - classification and gate rejects must not be ignored;
    - non-safety polish should become escalation/follow-up rather than infinite amendments.

## Files Allowed To Change

You may change:

    automation/scripts/analyze_story_run.sh
    automation/scripts/run_story.sh
    automation/scripts/refresh_review_evidence.sh
    automation/scripts/ai_review_story_run.sh
    automation/scripts/review_story_run.sh
    automation/scripts/classify_review_story_run.sh
    automation/scripts/review_gate_story_run.sh
    tests/test_analyze_story_run.py
    tests/test_run_story.py
    tests/test_refresh_review_evidence.py
    tests/test_ai_review_story_run.py
    tests/test_review_story_run.py
    tests/test_classify_review_story_run.py
    tests/test_review_classification_script.py
    tests/test_review_gate_story_run.py
    tests/test_review_pipeline_validation_contract.py
    docs/90_codex/US_AUTO_OPERATOR_GUIDE.md
    docs/90_codex/epics/US-AUTO_REGISTRY.md
    automation/bundle_packs/US-AUTO-58.bundle.md
    automation/bundles/active/US-AUTO-58/*

You may add a small helper module or helper script only if it keeps loop detection testable and follows existing project conventions.

## Files Not Allowed To Change

Do not change unrelated application or business feature files.

Do not change tests to weaken external behavior contracts.

Do not commit generated cache files.

Do not commit automation/runs artifacts.

Do not commit local environment files or secrets.

Do not broaden the story into US-AUTO-79 or US-AUTO-80.

## Requirements

Add loop-cap enforcement for repeated pipeline stage churn.

The implementation should detect repeated non-converging loops across at least:

    - run_story / rerun;
    - refresh_review_evidence;
    - analyze;
    - AI review;
    - classification;
    - review gate;
    - small fix / amend;
    - refresh again.

When the cap is reached, output a stable escalation marker and do not recommend another blind run_story or blind refresh.

The forced decision output must identify allowed next actions, such as:

    - narrow fix only for explicit safety/source-of-truth blocker;
    - follow-up for non-safety polish or broad refactor;
    - escalation for repeated evidence/fidelity churn;
    - abort or operator override only where existing policy allows;
    - use no-Codex refresh only when accepted implementation needs evidence refresh and the working tree is clean.

Keep analyze as the decision authority where possible.

Add tests for:

    - normal first-pass path not capped;
    - repeated run/rerun loop capped;
    - repeated refresh/review/classify loop capped;
    - safety/source-of-truth blocker allows narrow fix path;
    - non-safety polish routes to escalation/follow-up;
    - dirty tree and stale evidence blockers remain intact.

Update documentation in US_AUTO_OPERATOR_GUIDE.md to describe the stage-loop cap policy.

Optionally clarify the US-AUTO-58 registry row, but do not mark it Implemented during the implementation PR unless the repository’s established workflow explicitly expects that. Registry closeout is separate after merge.

## Output

Implement the code, tests, and documentation updates.

Run targeted tests covering modified scripts.

Report:

    - files changed;
    - loop-cap behavior added;
    - tests run and results;
    - any follow-ups for US-AUTO-31, US-AUTO-79, or US-AUTO-80.

Do not claim full pytest unless full pytest was actually run.

Do not produce generated run artifacts as committed files.

