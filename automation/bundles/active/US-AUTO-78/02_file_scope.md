## Files Allowed To Change

- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `docs/90_codex/US_AUTO_OPERATOR_GUIDE.md`
- `automation/bundle_packs/US-AUTO-78.bundle.md`
- `automation/bundles/active/US-AUTO-78/**`

## Files Not Allowed To Change

- `automation/scripts/**`
- `automation/run_codex_task.sh`
- `tests/**`
- application/runtime bot code
- database migrations
- dependency files
- CI workflow files
- unrelated documentation

## Scope Notes

This is a governance/docs-only story.

No runtime behavior may change.

The registry may add new planned story rows for orchestration-line work, but must not duplicate detailed story-level contracts that belong in future bundle packs.

The active bundle files may only be produced by materialization. They must not be manually edited as the source of truth.

