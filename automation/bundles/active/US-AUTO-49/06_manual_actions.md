# Manual Actions — US-AUTO-49

## Required Human Actions
1. Save this bundle pack to:
   - `automation/bundle_packs/US-AUTO-49.bundle.md`

2. Materialize the bundle:
   - `automation/scripts/materialize_story_bundle.sh US-AUTO-49`

3. Validate the bundle:
   - `automation/scripts/validate_story_bundle.sh US-AUTO-49`

4. Update epic registry logic in:
   - `docs/90_codex/epics/US-AUTO_REGISTRY.md`
   - Set `US-AUTO-49` as the current blocker-follow-up with status `Bundle Ready`
   - Keep `US-AUTO-28-F1` blocked pending this orchestration fix
   - Keep notes that `US-AUTO-28-F1` should not be rerun before `US-AUTO-49` merges

5. Create a dedicated branch from updated `main`

6. Commit the materialized bundle artifacts for `US-AUTO-49`

7. Run the story:
   - `automation/scripts/run_story.sh US-AUTO-49`

8. Analyze the resulting latest run directory:
   - `automation/scripts/analyze_story_run.sh US-AUTO-49`

9. Continue normal review pipeline only if the run succeeds through scope validation and produces a reviewable implementation delta

10. After merge:
   - return to `main`
   - pull latest `main`
   - remove working branches
   - re-evaluate the registry and resume with `US-AUTO-28-F1`

## Completion Status
- Bundle drafted: complete
- Materialize required: pending
- Validate required: pending
- Registry sync required: pending
- Branch creation required: pending
- Bundle artifact commit required: pending
- Story run required: pending
- Run analysis required: pending
- Merge and rerun selection: pending
