# Master Prompt — US-AUTO-52

## Role
You are the implementation engineer for the US-AUTO pipeline, working under strict fail-closed governance and atomic task isolation.

## Goal
Implement a strict manual-finish continuation contract so that continuation is allowed only for the exact committed manual-finish case tied to a previously blocked non-converging rerun, and rejected for broader ancestor-based or descendant-based cases.

## Source of Truth
Use only these files as the source of truth for this story:
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `tests/test_analyze_story_run.py`
- `tests/test_review_gate_story_run.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Files Allowed To Change
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `tests/test_analyze_story_run.py`
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
- any unrelated tests, scripts, docs, or workflow helpers outside the allowed list

## Atomic Task Isolation Contract
This is a narrow corrective follow-up. You may not redesign pipeline flow, create new recovery modes, or touch unrelated review stages. The only permitted functional change is tightening the continuation predicate and aligning direct regression coverage/documentation for that exact contract. If a desired fix requires broadening scope, stop and record a follow-up instead of implementing it.

## Execution Gate
Before making changes, verify that the intended edits remain within the allowed files and directly support the strict exact-case continuation contract. If you find yourself needing to:
- alter run orchestration,
- change AI review generation,
- modify bundle validator behavior,
- adjust unrelated stale-head policies,
then stop because the story boundary would be violated.

## Implementation Requirements
1. Preserve the proven capability that a valid manual-finish continuation path can proceed.
2. Remove any ancestor-based continuation logic that permits broader-than-intended acceptance.
3. Require the exact committed manual-finish case associated with the blocked run evidence.
4. Ensure analyze/classify/gate interpret that exact-case rule consistently.
5. Keep the implementation fail-closed when evidence is missing, stale, inconsistent, or refers to a different HEAD relationship.
6. Do not add fallback heuristics or best-effort continuation behavior.
7. Update documentation only as needed to describe the strict contract and the corrective story sequencing in the registry.

## Verification Requirements
You must verify, at minimum:
- exact allowed case passes,
- descendant commit after manual finish rejects,
- ancestor-based continuation rejects,
- existing committed-HEAD and stale-run protections still pass,
- no unrelated tests or files were changed.

Use targeted pytest coverage for the touched scripts. The implementation is not complete until regression tests explicitly prove the narrow exact-case behavior.

## Output
Produce only the implementation required for this story. Keep changes minimal and deterministic. Do not include speculative follow-ups in code. If additional defects are discovered, record them in documentation or follow-up notes without widening the implementation.

