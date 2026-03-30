## Required Human Actions

1. Save this bundle pack to `automation/bundle_packs/US-AUTO-53.bundle.md`.
2. From the repository root on the local machine, run:
   - `automation/scripts/materialize_story_bundle.sh US-AUTO-53`
   - `automation/scripts/validate_story_bundle.sh US-AUTO-53`
3. Update `docs/90_codex/epics/US-AUTO_REGISTRY.md` conservatively so:
   - `US-AUTO-53` is registered as a new P1 follow-up for the committed-HEAD `review_diff_patch_mismatch` blocker
   - `US-AUTO-53` becomes the first next recommended story
   - `US-AUTO-28-F1` remains blocked until US-AUTO-53 is merged
4. Create a dedicated feature branch from updated `main`.
5. Commit the story artifacts before running automation.
6. Run the story on the feature branch:
   - `automation/scripts/run_story.sh US-AUTO-53`
7. After implementation commit, rerun the story on the new committed HEAD and then analyze the fresh run:
   - `automation/scripts/analyze_story_run.sh US-AUTO-53`
8. Do not reuse any previous `AUTOMATION_RUN_DIR` after a new commit.
9. Only proceed to review and gate using evidence from the latest rerun aligned to current HEAD.

## Completion Status

- Bundle drafted: complete
- Materialize: pending
- Validate: pending
- Registry update: pending
- Branch creation: complete
- Story-artifact commit: pending
- Implementation: pending
- Fresh rerun on committed HEAD: pending
- Analyze latest run: pending
- Review and gate: pending
- Merge: pending
