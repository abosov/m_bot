# US-AUTO-42: File Scope

## Files Allowed To Change
- `automation/scripts/run_story.sh`
- `tests/test_run_story.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/US-AUTO-42.bundle.md`
- `automation/bundles/active/US-AUTO-42/**`

## Files Not Allowed To Change
- `automation/run_codex_task.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/escalate_story.sh`
- `automation/scripts/story_change_ledger.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `backend/**`
- `frontend/**`
- `database/**`
- `scripts/migrations/**`

## Scope Notes
- Keep the implementation confined to the invalid escalation resolution path in `run_story.sh`.
- Prefer the smallest deterministic parser/branching change that achieves fail-closed behavior.
- Tests must target blocking behavior, not broader workflow redesign.
- If a needed fix appears to require changing escalation artifact producers or neighboring scripts, stop and create a follow-up instead.

