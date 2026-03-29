## Role
You are a strict pipeline governance enforcer.

## Goal
Ensure the generated ChatGPT review prompt enforces a strict structured AI review output, allow a fresh rerun on the current HEAD after manual finish, and align the downstream review pipeline to accept and validate the new structured output contract.

## Source of Truth
- AI review output artifact
- Required structure sections

## Files Allowed To Change
- automation/run_codex_task.sh
- automation/scripts/run_story.sh
- automation/scripts/ai_review_story_run.sh
- automation/scripts/analyze_story_run.sh
- automation/scripts/classify_review_story_run.sh
- automation/scripts/review_gate_story_run.sh
- tests/test_run_codex_task.py
- tests/test_run_story.py
- tests/test_ai_review_story_run.py
- tests/test_analyze_story_run.py
- tests/test_classify_review_story_run.py
- tests/test_review_classification_script.py
- tests/test_review_gate_story_run.py
- tests/test_review_pipeline_validation_contract.py

## Files Not Allowed To Change
- automation/scripts/finalize_story.sh
- automation/scripts/materialize_story_bundle.sh
- automation/scripts/validate_story_bundle.sh
- automation/bundle_packs/*
- automation/bundles/active/*

## Atomic Task Isolation Contract
- Only enforce output structure
- Do not expand scope
- Do not refactor unrelated code
- Stop immediately on scope violation

## Out of Scope
- Changes to automation/scripts/finalize_story.sh
- Changes to automation/scripts/materialize_story_bundle.sh
- Changes to automation/scripts/validate_story_bundle.sh
- Changes outside run_codex_task / run_story / ai_review / classify / gate / analyze and their direct tests

## Implementation Requirements
1. Update the generated ChatGPT review prompt in automation/run_codex_task.sh
2. Require the output sections:
   - "# AI Review"
   - "# AI Review Result"
3. Require the prompt to forbid any preamble before "# AI Review"
4. Update tests/test_run_codex_task.py to verify the generated prompt contract
5. Update automation/scripts/run_story.sh so a manual-finish commit on a newer HEAD allows a fresh rerun instead of forcing review against stale run evidence
6. Update tests/test_run_story.py to cover the rerun-after-manual-finish path
7. Update downstream review scripts only as needed to validate and process the new structured AI review contract
8. Update the direct downstream tests to match the new contract

## Verification Requirements
- Generated prompt includes "## Required output format"
- Generated prompt includes "# AI Review"
- Generated prompt includes "# AI Review Result"
- Generated prompt includes "Do not output anything before # AI Review."
- tests/test_run_codex_task.py passes
- tests/test_run_story.py covers fresh rerun after manual finish on newer HEAD
- downstream review scripts accept or reject the new contract deterministically
- direct downstream tests pass for the structured AI review contract

## Output
- Deterministic generator-side review prompt contract
- Narrow diff limited to run_codex_task.sh and tests/test_run_codex_task.py

---

