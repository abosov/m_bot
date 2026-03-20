
# US-AUTO-22: Manual Actions

## Required Human Actions

- Fill in final PR metadata fields after implementation and review.
- Run bundle materialization and validation locally before starting Codex execution.

## Execution Notes

- This story should not proceed into implementation until the active bundle is fully materialized and validated.
- Confirm the master and follow-up prompts both include a one-sentence intent declaration requirement before edits and state that Atomic Task Isolation is a mandatory execution contract.
- Confirm the master and follow-up prompts both treat missing or ambiguous intent, out-of-scope, file-boundary, follow-up-capture, and hard-stop fields as execution blockers.
- Confirm follow-up prompts explicitly state that follow-up mode is not an exception path around Atomic Task Isolation and cannot batch a second independently reviewable fix.
- If implementation pressure pushes toward script enforcement, stop and create a separate story instead.
- If review yields multiple independent findings, split them into separate follow-up prompts before the next run.

## Completion Status

-  No manual actions required
-  Manual actions completed and documented
