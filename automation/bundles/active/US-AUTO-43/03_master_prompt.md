# US-AUTO-43 PROMPT 1 — AI Review Validation Contract

## Role
You are a Zumbot automation engineer enforcing strict pipeline governance.

## Goal
Ensure AI review stage enforces fail-closed validation so classification never runs on invalid artifacts.

## Source of Truth
- automation/scripts/ai_review_story_run.sh
- automation/scripts/classify_review_story_run.sh
- automation/scripts/review_gate_story_run.sh
- automation/scripts/analyze_story_run.sh

## Files Allowed To Change
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `tests/test_ai_review_story_run.py`
- `tests/test_review_pipeline_validation_contract.py`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/US-AUTO-43.bundle.md`
- `automation/bundles/active/US-AUTO-43/**`

## Files Not Allowed To Change
- automation/scripts/run_story.sh
- automation/run_codex_task.sh
- bundle system
- ledger
- git handling

## Output
Implement strict validation so:
- missing/malformed/incomplete outputs fail closed
- classification is blocked on invalid input
- failure states are deterministic and observable

