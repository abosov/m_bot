## Files Allowed To Change

Primary implementation files:

- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`

Primary test files:

- `tests/test_classify_review_story_run.py`
- `tests/test_review_gate_story_run.py`

Story governance artifacts:

- `automation/bundle_packs/US-AUTO-76.bundle.md`
- `automation/bundles/active/US-AUTO-76/00_story.md`
- `automation/bundles/active/US-AUTO-76/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-76/02_file_scope.md`
- `automation/bundles/active/US-AUTO-76/03_master_prompt.md`
- `automation/bundles/active/US-AUTO-76/04_review_checklist.md`
- `automation/bundles/active/US-AUTO-76/05_followups.md`
- `automation/bundles/active/US-AUTO-76/06_manual_actions.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

Optional only if directly required by existing test organization:

- no additional files by default

## Files Not Allowed To Change

Do not change:

- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/run_story.sh`
- `automation/scripts/commit_story_artifacts.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/scripts/new_story_bundle.sh`
- `automation/scripts/escalate_story.sh`
- `automation/scripts/finalize_story.sh`
- `automation/story_change_ledger.jsonl`
- `docs/90_codex/US_AUTO_OPERATOR_GUIDE.md`
- `automation/scripts/next_step.sh`
- unrelated files under `docs/**`
- unrelated files under `automation/bundle_packs/**`
- unrelated files under `automation/bundles/active/**`

Do not change tests to weaken existing behavior.

Do not modify tests in a way that removes or dilutes external contract expectations.

Do not change broad pipeline behavior outside classifier/review-gate semantics.

Do not edit materialized active bundle files manually after materialization; update the bundle pack and re-materialize instead.

