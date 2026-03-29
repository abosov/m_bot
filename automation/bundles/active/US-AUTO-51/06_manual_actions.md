# US-AUTO-51 — Manual Actions

## Required Human Actions
1. Create the bundle pack file:
   `automation/bundle_packs/US-AUTO-51.bundle.md`

2. Materialize the bundle:
   `automation/scripts/materialize_story_bundle.sh US-AUTO-51`

3. Validate the materialized bundle:
   `automation/scripts/validate_story_bundle.sh US-AUTO-51`

4. Update the epic registry during the story handoff:
   - add `US-AUTO-51` as a new P1 follow-up with status `Bundle Drafted` (or `In Progress` once work begins);
   - set `US-AUTO-51` as the effective blocker follow-up for the parked `US-AUTO-28-F1` path;
   - keep `US-AUTO-28-F1` status as `Blocked` with next action `Resume after US-AUTO-51 merges`;
   - keep `US-AUTO-50` as implemented / complete.

5. Create the feature branch:
   `git checkout -b feat/us-auto-51-manual-finish-review-continuation`

6. Commit the bundle artifacts before execution:
   - `automation/bundle_packs/US-AUTO-51.bundle.md`
   - `automation/bundles/active/US-AUTO-51/**`
   - registry/checklist updates required by this story

7. Run the story:
   `automation/scripts/run_story.sh US-AUTO-51`

8. Analyze the latest run:
   `automation/scripts/analyze_story_run.sh US-AUTO-51`

9. After merge of `US-AUTO-51`, return to the parked implementation branch:
   - checkout `feat/us-auto-28-f1-run`
   - update from latest `main`
   - continue review/classify/gate on the pinned parked run evidence without rerunning `automation/scripts/run_story.sh US-AUTO-28-F1`

## Completion Status
- [ ] Bundle created
- [ ] Bundle materialized
- [ ] Bundle validated
- [ ] Registry updated consistently
- [ ] Story artifacts committed before run
- [ ] Focused tests executed
- [ ] Post-merge handoff back to parked `US-AUTO-28-F1` prepared
