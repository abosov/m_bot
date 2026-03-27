# US-AUTO-42: Manual Actions

## Required Human Actions
- Materialize the bundle pack for `US-AUTO-42`.
- Validate the materialized active bundle before any run.
- Review the active bundle files in Cursor before executing the story.
- If validator fails, fix the bundle pack first instead of patching active files manually.
- After implementation, manually inspect at least one invalid escalation case to confirm `run_story.sh` fails closed with deterministic guidance.

## Execution Notes
- Bundle pack source of truth: `automation/bundle_packs/US-AUTO-42.bundle.md`
- Materialize with: `automation/scripts/materialize_story_bundle.sh US-AUTO-42`
- Validate with: `automation/scripts/validate_story_bundle.sh US-AUTO-42`
- Open active files after successful validation:
  - `automation/bundles/active/US-AUTO-42/00_story.md`
  - `automation/bundles/active/US-AUTO-42/02_file_scope.md`
  - `automation/bundles/active/US-AUTO-42/03_master_prompt.md`

## Completion Status
- [ ] Bundle materialized
- [ ] Bundle validated
- [ ] Manual verification completed
- [ ] Ready for PR

## Additional Manual Verification
- Confirm the bundle contains exactly seven file sections.
- Confirm there are no nested `=== FILE: ... ===` markers inside section bodies.
- Confirm validation passes before `run_story.sh`.
- Confirm the implementation PR remains atomic and touches no forbidden files.
