# US-AUTO-37: Context Bundle

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `automation/scripts/run_story.sh`
- `automation/scripts/finalize_story.sh`
- `automation/run_codex_task.sh`

## Current Code Reality
- `automation/story_change_ledger.jsonl` is a workflow-generated side effect.
- Existing scripts exclude this path from strict implementation-diff enforcement.
- Happy-path workflow should restore this path to `HEAD` on exit to keep the branch clean.

## Architectural Intent
- Introduce one explicit contract for ephemeral automation paths.
- Keep runtime-generated artifacts from masquerading as normal implementation diffs.
- Preserve strict validation for real code and workflow changes.

## Risks
- A too-broad ignore rule could hide real implementation changes.
- A too-local fix could reintroduce drift between scripts, tests, and docs.
- Incomplete lifecycle handling could fix run but still leave finalize dirty, or vice versa.

## Acceptance Notes
- Happy-path run should not leave ledger dirt in the working tree.
- Happy-path finalize should not leave ledger dirt in the working tree.
- Scope handling must remain strict for non-ephemeral file changes.
