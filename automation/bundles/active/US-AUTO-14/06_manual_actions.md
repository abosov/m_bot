# US-AUTO-14: Manual Actions

## Required Human Actions
- Run one real story through the pipeline with a valid in-scope diff.
- Run one negative check with a deliberately out-of-scope file and confirm fail-fast behavior.
- Inspect the failure message for clarity.
- Confirm the guard blocks the run before pytarts.

## Execution Notes
- Preferred verification path:
  - materialize the bundle
  - run the story on a feature branch
  - inspect `automation/runs/<STORY_ID>/<RUN_ID>/changed_files.txt`
  - confirm allowed-files validation behavior against real runner artifacts

## Completion Status
- [ ] No manual actions required
- [ ] Manual actions completed and documented
