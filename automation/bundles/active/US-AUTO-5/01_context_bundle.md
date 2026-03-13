# US-AUTO-5: Context Bundle

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/REVIEW_CLASSIFICATION_RULES.md`
- `automation/scripts/review_story_run.sh`

## Current Code Reality
- Latest-run resolution already exists for review-oriented workflows
- Existing run artifacts already include review bundle and prompt material
- There is no standardized artifact that records the AI review result for a run

## Target Architecture
- Reuse latest-run resolution and existing review artifacts
- Add one thin script for AI review execution/recording
- Store the result in the run directory for auditability
- Keep implementation isolated from runtime product code

## Risks
- Conflating review preparation with automatic remediation
- Producing inconsistent result formats across runs
- Overcomplicating the script instead of keeping it simple

## Acceptance Notes
- The script works for a story with at least one existing run
- The script fails clearly for missing runs or missing required artifacts
- The script creates a durable review-result artifact
