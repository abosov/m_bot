# Master Prompt — US-AUTO-48

## Role
You are implementing a narrow governance follow-up in the Zumbot automation pipeline. Work as a careful maintainer operating under strict atomic-task isolation.

## Goal
Harden the AI review artifact contract so the pipeline deterministically creates a valid normalized `ai_review_result.md` or fails closed with explicit evidence when normalization is impossible.

## Source of Truth
Use only the following as source of truth:
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- the active `US-AUTO-48` bundle files
- current implementations of:
  - `automation/scripts/ai_review_story_run.sh`
  - `automation/scripts/classify_review_story_run.sh`
  - `automation/scripts/review_gate_story_run.sh`
  - `automation/scripts/analyze_story_run.sh`
- corresponding focused tests

## Files Allowed To Change
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `tests/test_ai_review_story_run.py`
- `tests/test_classify_review_story_run.py`
- `tests/test_review_gate_story_run.py`
- `tests/test_analyze_story_run.py`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Files Not Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/run_codex_task.sh`
- `automation/scripts/finalize_story.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/story_change_ledger.jsonl`

## Output
Produce the smallest safe patch that:
- makes the normalized AI review artifact contract explicit and validated
- prevents malformed or incomplete AI review output from silently advancing
- makes classification and gate fail closed deterministically when normalized artifact validation fails
- preserves raw AI review output for debugging
- adds focused regression tests
- avoids unrelated scope expansion

Before editing, restate the one-sentence task intent.
If a required fix falls outside allowed scope, stop and record it in follow-ups instead of widening the patch.

