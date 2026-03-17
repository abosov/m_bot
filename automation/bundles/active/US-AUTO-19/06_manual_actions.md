# US-AUTO-19: Manual Actions

## Required Human Actions
- Materialize the bundle pack into `automation/bundles/active/US-AUTO-19/`
- Run the new analysis command against at least one existing story run
- Confirm the output is materially faster to inspect than opening artifacts manually

## Execution Notes
- Run locally:
  - `automation/scripts/materialize_story_bundle.sh US-AUTO-19`
  - `automation/scripts/validate_story_bundle.sh US-AUTO-19`
  - implement the story changes
  - `pytest tests/test_analyze_story_run.py`
- Suggested manual checks:
  - `automation/scripts/analyze_story_run.sh US-AUTO-17`
  - `AUTOMATION_RUN_DIR=<specific-run-dir> automation/scripts/analyze_story_run.sh US-AUTO-17`

## Completion Status
- [ ] Manual verification completed
- [ ] Ready for PR
