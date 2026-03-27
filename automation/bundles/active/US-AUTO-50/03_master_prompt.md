## Role
You are a strict pipeline governance enforcer.

## Goal
Ensure AI review always produces a valid structured output and never allows invalid or unstructured responses to proceed.

## Source of Truth
- AI review output artifact
- Required structure sections

## Files Allowed To Change
- automation/scripts/ai_review_story_run.sh
- automation/scripts/review_story_run.sh
- automation/scripts/classify_review_story_run.sh
- automation/scripts/review_gate_story_run.sh
- automation/scripts/analyze_story_run.sh
- tests/test_ai_review_story_run.py
- tests/test_review_pipeline.py

## Files Not Allowed To Change
- automation/run_codex_task.sh
- automation/scripts/run_story.sh
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

## Execution Gate
- If output is invalid → STOP
- Do not proceed to classification
- Fail-closed always

## Implementation Requirements
1. Validate presence of:
   - "# AI Review"
   - "# AI Review Result"
2. Detect echo:
   - output identical or highly similar to prompt
3. Detect empty/malformed output
4. On failure:
   - emit reason: ai_review_normalization_failed
   - stop pipeline
5. Maintain compatibility with valid outputs

## Verification Requirements
- Invalid output → rejected
- Valid output → passes unchanged
- No regression in existing flows

## Output
- Deterministic structured validation
- Explicit failure reason

---

