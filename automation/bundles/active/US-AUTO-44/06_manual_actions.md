# US-AUTO-44: Manual Actions

## Required Human Actions
- Rebuild the bundle pack after any bundle edits.
- Materialize the active bundle before execution when needed.
- If preflight reports requested-story artifact dirtiness:
  - review changes
  - run `automation/scripts/commit_story_artifacts.sh <STORY_ID>`
  - rerun `automation/scripts/run_story.sh <STORY_ID>`
- If preflight reports unrelated dirty paths:
  - resolve those changes outside the story-artifact handoff flow
  - rerun `automation/scripts/run_story.sh <STORY_ID>`
- Continue review → classify → review_gate after a successful run.

## Completion Status

### Current State
- Bundle prepared.
- Story defined as narrow preflight/operator-handoff contract work.
- Awaiting materialization, implementation, and review.

### Expected Operator Flow
1. `automation/scripts/materialize_story_bundle.sh US-AUTO-44`
2. `automation/scripts/run_story.sh US-AUTO-44`
3. if blocked by requested-story artifacts:
   - `automation/scripts/commit_story_artifacts.sh US-AUTO-44`
   - `automation/scripts/run_story.sh US-AUTO-44`
4. if blocked by unrelated dirtths:
   - resolve them outside the handoff flow
   - `automation/scripts/run_story.sh US-AUTO-44`
5. review → classify → review_gate
6. open PR and finalize via standard US-AUTO flow

### Registry Expectation
Update `docs/90_codex/epics/US-AUTO_REGISTRY.md` so US-AUTO-44 is visible as the explicit preflight/operator-handoff story following the commit-handoff work introduced earlier.
