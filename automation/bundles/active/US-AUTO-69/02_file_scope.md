## Files Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/run_codex_task.sh`
- `tests/test_run_story.py`
- `tests/test_run_codex_task.py`

## Files Not Allowed To Change
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/scripts/commit_story_artifacts.sh`
- `automation/story_change_ledger.jsonl`
- any file under `automation/bundles/active/` except through normal materialization before implementation
- any file under `automation/bundle_packs/` except this bundle before materialization
- any unrelated test file not listed above

## Scope Notes
Allowed change types:
- add a narrow companion-artifact classifier or predicate
- filter companion artifact paths from the effective execution review surface for code-only stories
- align any execution diff/evidence generation needed so filtered surfaces stay deterministic
- add focused tests covering companion-only allow, non-companion reject, and mixed-case reject

Hard boundaries:
- do not generalize into a universal path-policy framework
- do not modify review-stage contracts
- do not change registry content as part of runtime logic
- do not introduce telemetry, new CLI phases, or operator UX redesign
- do not relax fail-closed behavior for ambiguous or unknown paths

If implementation requires files outside this list, reject and spin a follow-up instead of expanding scope.

