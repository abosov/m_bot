# Review Checklist — US-AUTO-49

## Scope Validation
- Confirm only these files changed:
  - `automation/run_codex_task.sh`
  - `tests/test_run_codex_task.py`
- Reject if any forbidden file changed.
- Reject if the implementation ignores uncommitted artifacts.
- Reject if the implementation ignores artifacts for a different story ID.
- Reject if the implementation ignores non-canonical paths or uses loose substring matching.
- Reject if the implementation moves this logic into review, gate, finalize, or registry code.

## Functional Validation
- Confirm the runtime orchestration excludes only canonical committed bundle artifacts for the active story:
  - `automation/bundle_packs/<STORY_ID>.bundle.md`
  - `automation/bundles/active/<STORY_ID>/...`
- Confirm the active story ID is used as the matching boundary.
- Confirm ambiguous or unmatched paths are still validated normally.
- Confirm a true out-of-scope implementation file still fails the run.
- Confirm the change preserves fail-closed semantics.

## Verification
### Required Evidence
- targeted test execution for `tests/test_run_codex_task.py`
- evidence that same-story committed bundle artifacts do not cause a false scope reject
- evidence that a real out-of-scope implementation file still causes a reject

### HARD BLOCK — REJECT IF ANY APPLY
- any scope expansion beyond runtime orchestration and its tests
- any weakening of allowed-files enforcement
- any ignore rule broader than canonical same-story bundle artifacts
- any fallback path that continues when story identity or provenance is ambiguous
- missing regression coverage for the reject path
- review outcome cannot be expressed as binary `APPROVE` or `REJECT`

### Binary Decision
- **APPROVE** only if all scope, functional, and verification checks pass
- **REJECT** otherwise

