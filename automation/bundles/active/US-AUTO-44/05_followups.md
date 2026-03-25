# US-AUTO-44: Follow-Ups

## Follow-Up Prompt Queue
- Add a lightweight helper that previews classified dirty paths before the operator chooses a remediation action.
- Add a status command that prints workflow stage plus preflight classification without attempting execution.
- Consider a later story for richer operator UX around materialization readiness.
- Consider a later story for tighter integration between analyze output and preflight diagnostics.
- Revisit whether `commit_story_artifacts.sh` and `run_story.sh` should share a common read-only path-classification helper in a separate contract-focused story.

## Iteration Notes
- Keep US-AUTO-44 narrow and message-contract focused.
- Do not convert preflight into mutation.
- Do not redesign materialization.
- Prefer stable output over clever behavior.

## Deferred Questions
- Should preflight output become machine-readable in a later story?
- Should analyze consume the same preflight classification helper in a later story?
- Should there be a dedicated `check_story_ready.sh` helper, or is that unnecessary duplication?

