# US-AUTO-24: File Scope

## Files Allowed To Change
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/US-AUTO-24.bundle.md`
- `automation/bundles/active/US-AUTO-24/00_story.md`
- `automation/bundles/active/US-AUTO-24/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-24/02_file_scope.md`
- `automation/bundles/active/US-AUTO-24/03_master_prompt.md`
- `automation/bundles/active/US-AUTO-24/04_review_checklist.md`
- `automation/bundles/active/US-AUTO-24/05_followups.md`
- `automation/bundles/active/US-AUTO-24/06_manual_actions.md`

## Files Not Allowed To Change
- `automation/run_codex_task.sh`
- `automation/scripts/run_story.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/finalize_story.sh`
- `automation/scripts/story_change_ledger.sh`
- `tests/**`
- `backend/**`
- `frontend/**`
- `database/**`
- `migrations/**`

## Scope Notes
- This story is design-only and must not implement runtime workflow changes.
- Update only the registry, the new bundle pack, and the materialized `US-AUTO-24` active bundle files.
- The bundle must explicitly define the canonical event model, durability contract, review artifact consistency rules, clean-tree boundary, finalization semantics, and operator workflow.
- If the design appears to require a runtime implementation change, describe it as a downstream implementation story rather than changing scripts here.
