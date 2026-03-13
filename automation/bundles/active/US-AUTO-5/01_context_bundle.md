# US-AUTO-5: Context Bundle

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/REVIEW_CLASSIFICATION_RULES.md`
- `automation/scripts/review_story_run.sh`

## Current Code Reality
- Latest-run resolution already exists for review-oriented workflows
- Existing run artifacts already include `review_bundle.md` and `chatgpt_review_prompt.md`
- There is no script that executes an AI review command and stores the actual review output for a run

## Target Architecture
- Reuse latest-run resolution and existing review artifacts
- Add one thin script for AI review execution and output recording
- Store the actual AI review output in the run directory for auditability
- Keep implementation isolated from runtime product code

## Risks
- Conflating review execution with automatic remediation
- Producing placeholder artifacts instead of real review output
- Overcomplicating the script instead of keeping it simple

## Acceptance Notes
- The script works for a story with at least one existing run
- The script fails clearly for missing runs or missing required artifacts
- The script writes actual AI review output, not a TBD template
