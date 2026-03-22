# US-AUTO-39: File Scope

## Files Allowed To Change

- `automation/scripts/finalize_story.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/run_story.sh`
- `automation/scripts/run_codex_task.sh`
- `tests/test_finalize_story_script.py`
- `tests/test_review_gate_story_run.py`
- `automation/story_change_ledger.jsonl`
- `docs/90_codex/**`
- `automation/bundles/active/US-AUTO-39/**`
- `automation/bundle_packs/US-AUTO-39.bundle.md`

## Files Not Allowed To Change

- `backend/**`
- `frontend/**`
- `database/**`
- `migrations/**`
- unrelated deployment scripts
- unrelated bundle packs
- broad workflow redesign outside HEAD-bound post-finalize approval

## Scope Notes

- Keep this story narrowly focused on post-finalize re-review / re-gate contract enforcement.
- Do not absorb US-AUTO-40 / US-AUTO-41 / US-AUTO-35 / US-AUTO-36 / US-AUTO-37 / US-AUTO-38 except for minimal shared plumbing strictly required here.

