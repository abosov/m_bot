# US-AUTO-38: Context Bundle

## Source of Truth
- `automation/scripts/run_story.sh`
- `automation/run_codex_task.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- tests covering story execution and cleanup behavior
- merged US-AUTO-37 workflow behavior

## Current Code Reality
- Ephemeral automation path cleanup is already improved after US-AUTO-37.
- `automation/story_change_ledger.jsonl` no longer drives false dirty-tree behavior in ordinary status/diff semantics.
- A story run may still enter a mutable execution window, fail or be interrupted, and leave partial changes behind.
- Operator cleanup after failed execution is still partially manual and not contractually defined.

## Architectural Intent
Treat story execution like a repository-scoped transaction:
- verify clean entry;
- capture a pre-run baseline;
- arm rollback before mutable execution;
- disarm rollback only at an explicit success boundary;
- on failure/interruption, restore tracked state and clean run-owned untracked artifacts;
- keep diagnostics visible without leaving the repository dirty by default.

Preferred ownership:
- top-level orchestration layer owns repository rollback lifecycle;
- lower-level runners may perform local cleanup but should not own the transaction boundary.

## Risks
- over-broad cleanup could remove more than intended;
- split rollback ownership could cause conflicting cleanup logic;
- rollback might trigger after success if disarm logic is weak;
- diagnostics could be lost if cleanup is too aggressive;
- new rollback behavior could regress US-AUTO-37 ephemeral path handling.

## Acceptance Notes
Accept the story only if:
- failed execution from a clean start restores the exact clean pre-run state;
- success preserves intended changes;
- rollback failure is surfaced loudly;
- regression tests confirm US-AUTO-37 behavior remains intact;
- docs clearly define when rollback applies and what it restores.

