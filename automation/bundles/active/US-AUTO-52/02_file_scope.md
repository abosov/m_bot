# File Scope — US-AUTO-52

## Files Allowed To Change
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `tests/test_analyze_story_run.py`
- `tests/test_classify_review_story_run.py`
- `tests/test_review_gate_story_run.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Files Not Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/run_codex_task.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/story_change_ledger.jsonl`
- any files under `automation/bundle_packs/` other than the materialized US-AUTO-52 artifacts created by workflow
- any files under `automation/bundles/active/` other than the materialized US-AUTO-52 artifacts created by workflow
- any unrelated tests or docs outside the files explicitly allowed above

## Scope Notes
- Allowed change types are limited to: tightening the manual-finish continuation predicate, aligning cross-script reasoning for the same predicate, adding exact regression tests for strict acceptance/rejection cases, and updating checklist/registry text to reflect the new corrective story.
- Do not widen scope into retry strategy, manual-finish UX, new operator prompts, or generalized stale-evidence recovery.
- Do not weaken tests to make the implementation pass; tests must enforce the strict external contract.
- `docs/90_codex/epics/US-AUTO_REGISTRY.md` changes must only reflect status/priority/next-story logic for US-AUTO-51, US-AUTO-52, and the dependency note for US-AUTO-28-F1.

