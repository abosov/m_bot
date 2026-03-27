# US-AUTO-45: Manual Actions

## Required Human Actions
- Materialize the bundle pack for `US-AUTO-45`.
- Validate the materialized active bundle before any run.
- Review the active bundle files in Cursor before executing the story.
- If validator fails, fix the bundle pack first instead of patching active files manually.

## Execution Notes
- Bundle pack source of truth: `automation/bundle_packs/US-AUTO-45.bundle.md`
- Materialize with: `automation/scripts/materialize_story_bundle.sh US-AUTO-45`
- Validate with: `automation/scripts/validate_story_bundle.sh US-AUTO-45`
- Open active files after successful validation:
  - `automation/bundles/active/US-AUTO-45/00_story.md`
  - `automation/bundles/active/US-AUTO-45/02_file_scope.md`
  - `automation/bundles/active/US-AUTO-45/03_master_prompt.md`

## Completion Status
- [ ] No manual actions required
- [ ] Manual actions completed and documented

## Additional Manual Verification
- Confirm the bundle contains exactly seven file sections.
- Confirm there are no nested `=== FILE: ... ===` markers inside section bodies.
- Confirm validation passes before `run_story.sh`.
