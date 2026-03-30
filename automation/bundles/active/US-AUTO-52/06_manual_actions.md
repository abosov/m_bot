# Manual Actions — US-AUTO-52

## Required Human Actions
1. Save this bundle pack to `automation/bundle_packs/US-AUTO-52.bundle.md`.
2. Run `automation/scripts/materialize_story_bundle.sh US-AUTO-52`.
3. Run `automation/scripts/validate_story_bundle.sh US-AUTO-52`.
4. Update `docs/90_codex/epics/US-AUTO_REGISTRY.md` consistently with this bundle:
   - mark US-AUTO-51 as blocked/rejected follow-up required,
   - add US-AUTO-52 as the current P1 next recommended corrective story,
   - keep US-AUTO-28-F1 blocked pending US-AUTO-52.
5. Create a new feature branch for US-AUTO-52. Do not run automation on `main`.
6. Commit the story artifacts for US-AUTO-52 before implementation work.
7. Implement the strict continuation fix only within the allowed files.
8. Run targeted pytest coverage for the touched scripts.
9. Run `automation/scripts/run_story.sh US-AUTO-52` from the current feature-branch HEAD.
10. After any new commit, treat prior `AUTOMATION_RUN_DIR` values as invalid and rerun the story before review-stage commands.
11. Run `automation/scripts/analyze_story_run.sh US-AUTO-52` on the fresh run.
12. Proceed with pinned review-stage commands only for the rerun produced from the current committed HEAD.

## Completion Status
- Bundle drafted for US-AUTO-52.
- Registry logic intended: US-AUTO-52 becomes the active corrective P1 follow-up.
- Implementation, verification, rerun, and review are pending.
