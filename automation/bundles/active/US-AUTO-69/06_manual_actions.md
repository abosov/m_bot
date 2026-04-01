## Required Human Actions
1. Save this bundle pack to `automation/bundle_packs/US-AUTO-69.bundle.md`.
2. Materialize the story bundle:
   - `automation/scripts/materialize_story_bundle.sh US-AUTO-69`
3. Validate the materialized bundle:
   - `automation/scripts/validate_story_bundle.sh US-AUTO-69`
4. Update the registry conservatively to reflect bundle readiness for US-AUTO-69 and keep US-AUTO-57 blocked until evidence changes. Source registry: `docs/90_codex/epics/US-AUTO_REGISTRY.md` :contentReference[oaicite:11]{index=11}
5. Create a feature branch for the story. Do not run automation on `main`.
6. Commit the bundle artifacts using the normal story-artifact handoff flow.
7. Run the story:
   - `automation/scripts/run_story.sh US-AUTO-69`
8. After the run completes, analyze the latest run before any further phase:
   - `automation/scripts/analyze_story_run.sh US-AUTO-69`
9. Only after committed implementation and a fresh rerun boundary are satisfied, continue into the ordinary review path according to current pipeline rules.

## Completion Status
- Bundle selected: complete
- Bundle drafted: complete
- Materialize: pending human action
- Validate: pending human action
- Registry update: pending human action
- Branch creation: pending human action
- Story-artifact commit handoff: pending human action
- Implementation run: pending human action
- Run analysis: pending human action
- Review and merge: pending human action
