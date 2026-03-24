# Manual Actions

## Required Human Actions
1. Save this bundle pack to:
   - `automation/bundle_packs/US-AUTO-28.bundle.md`
2. Materialize the bundle:
   - `automation/scripts/materialize_story_bundle.sh US-AUTO-28`
3. Validate the active bundle:
   - `automation/scripts/validate_story_bundle.sh automation/bundles/active/US-AUTO-28`
4. Update:
   - `docs/90_codex/epics/US-AUTO_REGISTRY.md`
5. Commit story artifacts before run:
   - `automation/scripts/commit_story_artifacts.sh US-AUTO-28`
6. Execute the story:
   - `automation/scripts/run_story.sh US-AUTO-28`

## Completion Status
- Bundle draft prepared
- Waiting for successful materialize
- Waiting for bundle validation
- Waiting for registry update
- Waiting for artifact commit handoff
- Waiting for story execution
