# US-AUTO-12: Context Bundle

## Source of Truth
- `automation/scripts/new_story_bundle.sh`
- `automation/scripts/run_story.sh`
- `automation/templates/story_bundle_template.md`
- `automation/templates/codex_master_prompt_template.md`
- `automation/templates/followup_prompt_template.md`
- `automation/templates/review_prompt_template.md`
- `automation/templates/pr_description_template.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `.github/workflows/no-placeholder-paths.yml`

## Current Code Reality
- `new_story_bundle.sh` currently creates a seven-file bundle directly from templates.
- `run_story.sh` currently checks file presence and then executes the runner.
- There is no bundle pack source file and no pre-run semantic validation.

## Architectural Intent
- Treat one bundle pack file as the canonical source of truth for each story.
- Materialize bundle files atomically from that single source.
- Validate required sections and unresolved placeholders before execution.

## Risks
- Existing manually created bundles may fail new validation until normalized.

## Acceptance Notes
- Materialization and validation are deterministic and script-driven.

