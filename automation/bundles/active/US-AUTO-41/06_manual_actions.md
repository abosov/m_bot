# US-AUTO-41: Manual Actions

## Required Human Actions
- Rebuild bundle pack after any bundle changes.
- Materialize the active bundle before execution.
- Commit story artifacts using `commit_story_artifacts.sh`.
- Run the story workflow using `run_story.sh`.
- Perform review, classification, and review gate steps.
- Open PR and finalize via the standard US-AUTO flow.

## Completion Status

### Current State
- Bundle draft prepared.
- Validator corrections applied.
- Awaiting stable materialization and clean review pass.

### Expected Operator Flow
1. `new_story_bundle.sh <STORY_ID>`
2. materialize bundle
3. `automation/scripts/commit_story_artifacts.sh <STORY_ID>`
4. `automation/scripts/run_story.sh <STORY_ID>`
5. review → classify → review_gate
6. finalize story via PR