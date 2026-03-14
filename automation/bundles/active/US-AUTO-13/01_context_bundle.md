# US-AUTO-13: Context Bundle

## Source of Truth
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- current `gh`-based story merge workflow already used in the repo
- project rule: after merge, switch to `main`, pull latest `main`, and delete local/remote working branches

## Current Code Reality
- Story execution is already automated through bundle materialization, validation, and runner scripts.
- PR creation and merge are currently performed via manual `gh` commands in the terminal.
- Final branch cleanup is currently manual discipline, not an enforced scripted workflow.

## Architectural Intent
- Add one explicit finalization layer after story implementation and PR readiness.
- Keep finalization separate from story execution and review scripts.
- Make `gh` the canonical integration point for GitHub operations.

## Risks
- GitHub network/transient failures can interrupt finalize flow.
- Parsing CLI output too loosely could hide real failures.

## Acceptance Notes
- Scripted finalization must be deterministic and fail fast.
- Finalization must preserve the project's no-stale-branches rule.

