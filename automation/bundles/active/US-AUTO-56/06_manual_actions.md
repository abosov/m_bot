## Required Human Actions
1. Save this bundle pack to `automation/bundle_packs/US-AUTO-56.bundle.md`.
2. Run `automation/scripts/materialize_story_bundle.sh US-AUTO-56`.
3. Run `automation/scripts/validate_story_bundle.sh US-AUTO-56`.
4. Update `docs/90_codex/epics/US-AUTO_REGISTRY.md` conservatively so US-AUTO-56 reflects bundle readiness / active work state and remains the current priority story until merged.
5. Create a feature branch for US-AUTO-56. Do not run automation on `main`.
6. Commit the bundle artifacts using the normal story-artifact handoff workflow.
7. Run `automation/scripts/run_story.sh US-AUTO-56`.
8. Run `automation/scripts/analyze_story_run.sh US-AUTO-56`.
9. Only proceed to review-stage commands if the resulting stage-gate guidance explicitly permits it.

## Completion Status
- Story selection completed: US-AUTO-56 chosen as the highest-priority next story with completed dependencies.
- Atomicity check completed: narrow guidance-only scope confirmed.
- Bundle sanity check completed: seven required files present with required headings and synchronized scope.
- Implementation status: not started.
