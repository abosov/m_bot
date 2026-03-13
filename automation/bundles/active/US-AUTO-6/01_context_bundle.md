# US-AUTO-6: Context Bundle

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/REVIEW_CLASSIFICATION_RULES.md`
- `automation/scripts/ai_review_story_run.sh`

## Current Code Reality
- Latest-run resolution already exists in the review-oriented automation scripts
- Existing run artifacts can include `ai_review_result.md` from `automation/scripts/ai_review_story_run.sh`
- There is no script that executes a standardized classification step and stores the classification result for a run

## Target Architecture
- Reuse latest-run resolution and existing AI review artifacts
- Add one thin script for classification execution and output recording
- Store the actual classification output in the run directory for auditability
- Keep implementation isolated from runtime product code and fix automation

## Risks
- Conflating classification with automatic remediation
- Producing placeholder artifacts instead of real classification output

## Acceptance Notes
- The script works for a story with at least one existing AI review artifact
- The script fails clearly for missing runs or missing `ai_review_result.md`
- The script writes actual classification output, not a TBD template
