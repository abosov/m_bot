# US-AUTO-28 PROMPT 1 — Escalation gate for repeated reject stagnation

## Goal
Implement a deterministic escalation layer that stops automated continuation when repeated reject outcomes show no meaningful progress and requires an explicit human decision before the story may proceed further.

## Role
You are the Workflow Architect, Bash/Python Automation Developer, QA Engineer, and Tech Writer for the Zumbot US-AUTO pipeline.

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- current scripts and tests for run/review/gate/analyze flow

## Files Allowed To Change
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/run_story.sh`
- `automation/scripts/escalate_story.sh`
- `tests/test_review_gate_story_run.py`
- `tests/test_analyze_story_run.py`
- `tests/test_run_story.py`
- `tests/test_escalate_story.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Files Not Allowed To Change
- unrelated automation scripts
- product application code
- unrelated stories / bundles
- GitHub Actions workflows unless directly required by this story
- broad classification taxonomy redesign

## Output
Produce a minimal, deterministic implementation that:
1. detects repeated reject stagnation
2. marks escalation as required
3. blocks ordinary automated continuation once escalation is required
4. provides an explicit operator command to resolve escalation through:
   - accept-as-is
   - force-followup
   - abort
5. surfaces escalation state clearly in artifacts / analysis output
6. adds focused tests and documentation updates

Keep the patch narrow. Do not absorb US-AUTO-25 or US-AUTO-26 into this story.

