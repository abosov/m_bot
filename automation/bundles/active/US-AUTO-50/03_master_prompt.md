## Role
You are a strict pipeline governance enforcer.

## Goal
Ensure the generated ChatGPT review prompt enforces a strict structured AI review output so the model produces the required markdown contract directly.

## Source of Truth
- AI review output artifact
- Required structure sections

## Files Allowed To Change
- automation/run_codex_task.sh
- tests/test_run_codex_task.py

## Files Not Allowed To Change
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

## Out of Scope
- Changes to automation/scripts/ai_review_story_run.sh
- Changes to automation/scripts/classify_review_story_run.sh
- Changes to automation/scripts/review_gate_story_run.sh
- Changes to automation/scripts/analyze_story_run.sh
- Changes to downstream validation, classification or gate logic

## Implementation Requirements
1. Update the generated ChatGPT review prompt in automation/run_codex_task.sh
2. Require the output sections:
   - "# AI Review"
   - "# AI Review Result"
3. Require the prompt to forbid any preamble before "# AI Review"
4. Update tests/test_run_codex_task.py to verify the generated prompt contract
5. Do not modify downstream review validation, classification, gate, or analysis logic

## Verification Requirements
- Generated prompt includes "## Required output format"
- Generated prompt includes "# AI Review"
- Generated prompt includes "# AI Review Result"
- Generated prompt includes "Do not output anything before # AI Review."
- tests/test_run_codex_task.py passes

## Output
- Deterministic generator-side review prompt contract
- Narrow diff limited to run_codex_task.sh and tests/test_run_codex_task.py

---

