
## Required Human Actions

* automation/scripts/commit_story_artifacts.sh US-AUTO-75
* automation/scripts/run_story.sh US-AUTO-75
* automation/scripts/analyze_story_run.sh US-AUTO-75

## Completion Status

* Always use latest run
* Do not reuse old run
* Review only after committed-head rerun
* Gate only on pinned artifacts
* If successful materialization leaves a dirty workspace, commit the materialized implementation changes before running review-stage commands
