# US-AUTO-51 — File Scope

## Files Allowed To Change
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `tests/test_analyze_story_run.py`
- `tests/test_classify_review_story_run.py`
- `tests/test_review_gate_story_run.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/US-AUTO-51.bundle.md`
- `automation/bundles/active/US-AUTO-51/**`

## Files Not Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/run_codex_task.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/finalize_story.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `tests/test_run_story.py`
- `tests/test_run_codex_task.py`
- `tests/test_ai_review_story_run.py`
- `backend/**`
- `frontend/**`
- `database/**`
- `migrations/**`
- `.github/workflows/**`
- unrelated bundle packs
- the parked implementation branch contents for `US-AUTO-28-F1`

## Scope Notes
- Keep this story narrowly focused on downstream continuation after manual finish.
- Do not redesign rerun detection.
- Do not redesign AI review generation or validation.
- Do not absorb `US-AUTO-28-F1` implementation changes into this story.
- Allowed change types:
  - narrow continuation predicate logic;
  - aligned operator/analyze messaging;
  - direct regression tests;
  - minimal documentation and registry updates required by the new contract.
- Hard anti-scope-drift rule:
  - if a patch changes run-stage behavior, AI review-stage behavior, or generic stale-head semantics outside the manual-finish continuation case, reject it.

