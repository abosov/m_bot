## Files Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/scripts/_helpers.sh`
- `tests/test_run_story.py`

## Files Not Allowed To Change
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/run_codex_task.sh`
- `automation/story_change_ledger.jsonl`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/*`
- `automation/bundles/active/*`
- Any unrelated tests outside `tests/test_run_story.py`

## Scope Notes
- Allowed change types:
  - add preflight helper logic for rerun-skip detection
  - read existing run evidence conservatively
  - emit deterministic operator guidance
  - add or adjust focused tests only for the new preflight behavior in `tests/test_run_story.py`
- Forbidden change types:
  - changing analyze semantics
  - changing review-stage script inputs or outputs
  - changing manual-finish continuation rules
  - adding telemetry persistence
  - changing registry structure
  - changing bundle materialization or validation contracts
- Anti-scope-drift rule:
  - do not implement analyze enforcement, stage-loop escalation, artifact reuse, or lightweight artifact refresh in this story
- Fail-closed rule:
  - on uncertainty, missing evidence, stale evidence, parse failure, or ambiguous comparison, do not skip the rerun

