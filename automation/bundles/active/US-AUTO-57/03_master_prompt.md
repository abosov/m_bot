## Role
You are the implementation engineer for US-AUTO-57 working inside the Codex automation pipeline with strict fail-closed workflow rules.

## Goal
Implement a narrow preflight rerun-skip detector in `automation/scripts/run_story.sh` that blocks a new Codex rerun only when the pipeline can conservatively prove that rerunning would not change the effective review surface for the current committed state.

## Source of Truth
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/scripts/run_story.sh`
- Existing run evidence format already consumed by the pipeline
- Existing workflow invariants from US-AUTO-41, US-AUTO-44, US-AUTO-46, US-AUTO-47, US-AUTO-52, and US-AUTO-56

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

## Atomic Task Isolation Contract
- Solve one problem only: prevent a wasted rerun before Codex execution when sameness is provable.
- Do not implement mandatory analyze gating.
- Do not implement stage-loop counters or escalation.
- Do not implement review-artifact reuse or lightweight review refresh.
- Do not relax committed-HEAD, manual-finish, or review-boundary contracts.
- Hard stop: if the change requires broad orchestration redesign, stop and keep the implementation within the allowed files and narrow preflight boundary.

## Execution Gate
- The new logic must run before Codex execution starts.
- The new logic must preserve all existing preflight gates.
- The new logic must be fail-closed:
  - if evidence is missing, ambiguous, stale, malformed, or inconsistent, do not skip
  - if proof of sameness exists, stop the rerun and emit deterministic guidance
- The skip decision must not mutate existing run artifacts and must not fabricate new review evidence.

## Implementation Requirements
- Use existing committed-head and run-evidence concepts already present in the pipeline rather than inventing a new external state source.
- Detect the narrow safe case where the current story already has prior run evidence for the same effective committed review surface and a new rerun would not change that surface.
- Emit a deterministic reason string and guidance message that clearly explains that the rerun is being blocked because it would not change the effective review surface.
- Keep the implementation conservative:
  - sameness must be proven, not assumed
  - uncertainty must fall through to the ordinary run path
- Preserve the current successful paths when skip is not provable.
- Preserve branch-safety, dirty-state classification, and story-artifact handoff behavior already implemented in the pipeline.
- Keep helper extraction small and local if needed; avoid broad utility redesign.
- Keep console messaging aligned with the operator-guidance style introduced by US-AUTO-56.

## Verification Requirements
- Add focused automated coverage in `tests/test_run_story.py` for:
  - rerun blocked when safe sameness proof exists
  - rerun proceeds when no prior proof exists
  - rerun proceeds when evidence is stale, malformed, or ambiguous
  - skip path does not invoke Codex execution
  - skip path emits deterministic guidance
- Do not modify unrelated tests to force green behavior.
- Preserve external contracts; fix internal logic rather than weakening expectations.

## Output
- A narrow implementation in the allowed files only
- Deterministic console guidance for the skip path
- Focused tests proving the new fail-closed preflight behavior
- No fallback modes
- No scope expansion beyond US-AUTO-57

