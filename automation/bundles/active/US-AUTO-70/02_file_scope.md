## Files Allowed To Change
- `automation/scripts/run_story.sh`
- `tests/test_run_story.py`

## Files Not Allowed To Change
- `automation/run_codex_task.sh`
- `tests/test_run_codex_task.py`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/commit_story_artifacts.sh`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/US-AUTO-69.bundle.md`
- `automation/bundles/active/US-AUTO-69/**`
- any other file not explicitly listed under Files Allowed To Change

## Scope Notes
Allowed change types:
- narrow logic changes in `run_story.sh` that recompute the effective filtered review surface for rerun-preflight
- small helper extraction or local refactor inside `run_story.sh` only if required to keep the behavior deterministic and testable
- targeted tests in `tests/test_run_story.py` that prove:
  - companion-filtered rerun-preflight uses the recomputed filtered surface
  - unchanged paths remain stable
  - failures remain fail-closed

Hard scope rules:
- no companion-filtering rule changes
- no registry editing in this implementation story
- no broad pipeline orchestration changes
- no telemetry, UX, cache, retry, or optimization work
- no fallback to stale or unfiltered surfaces

If implementation pressure suggests another file is needed, stop and treat that as evidence of a new follow-up rather than widening this story.

