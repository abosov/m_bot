# File Scope — US-AUTO-49

## Files Allowed To Change
- `automation/run_codex_task.sh`
- `tests/test_run_codex_task.py`

## Files Not Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/finalize_story.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/check_allowed_files.sh`
- `automation/story_change_ledger.jsonl`
- `automation/bundle_packs/US-AUTO-28-F1.bundle.md`
- `automation/bundles/active/US-AUTO-28-F1/**`
- `automation/bundle_packs/US-AUTO-49.bundle.md`
- `automation/bundles/active/US-AUTO-49/**`
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Scope Notes
- This is a narrow orchestration-only story.
- Allowed change types:
  - derive or refine runtime scope baseline for the active story
  - exclude canonical committed bundle artifacts for the same story from implementation-delta scope validation
  - add regression tests covering the ignore path and reject path
- Hard scope boundaries:
  - do not modify bundle format, registry logic, review logic, or gate logic
  - do not relax scope enforcement for any non-bundle implementation file
  - do not ignore artifacts for a different story ID
  - do not introduce heuristics that silently continue on ambiguous path matching
- Fail closed rule:
  - if the script cannot determine that a changed file is a canonical committed bundle artifact for the active story, it must be treated as a normal changed file and validated normally

