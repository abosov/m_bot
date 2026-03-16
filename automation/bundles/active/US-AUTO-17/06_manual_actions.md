# US-AUTO-17: Manual Actions

## Required Human Actions
- Materialize the bundle pack into `automation/bundles/active/US-AUTO-17/`
- Run the story on a feature branch, not on `main`
- Review generated run artifacts, especially:
  - `repository_map_runtime.md`
  - `story_context.md`
  - `manifest.md`
- Confirm the new runtime map is clearer and more useful than the baseline version

## Execution Notes
- Run locally:
  - `automation/scripts/materialize_story_bundle.sh US-AUTO-17`
  - `automation/scripts/validate_story_bundle.sh US-AUTO-17`
  - `automation/scripts/run_story.sh US-AUTO-17`
- Focus manual review on whether story-local context and architecture boundaries are both present and compact.
- Defer operator-facing UX improvements to follow-up stories rather than extending this story.

## Completion Status
- [ ] Manual verification completed
- [ ] Ready for PR
