## Source of Truth
- Read-only reference: `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/scripts/run_story.sh`
- `automation/scripts/analyze_story_run.sh`
- Existing committed-head run artifacts under `automation/runs/<STORY_ID>/...`
- The implemented workflow contracts from US-AUTO-41, US-AUTO-44, US-AUTO-46, US-AUTO-47, US-AUTO-52, and US-AUTO-56

## Current Code Reality
- The current preflight in `run_story.sh` focuses on dirty-state classification, story-artifact handoff, and branch-safety checks.
- Review-stage eligibility and manual-finish guidance are surfaced after runs and analysis, not before Codex execution.
- Repeated reruns can still happen even when the effective review surface for the current committed HEAD would remain unchanged.
- The registry identifies post-US-AUTO-56 remaining work as cycle-cost reduction, early stopping, better decision gates, safer reuse, and observability.

## Architectural Intent
- Add an early fail-closed stop only where sameness is provable.
- Reuse existing committed-head evidence concepts rather than inventing a second workflow truth.
- Reduce wasted execution cost without weakening review integrity or manual-finish correctness.
- Keep the change narrow: preflight detection only, no orchestration redesign.
- Preserve separation of concerns:
  - US-AUTO-57 handles early rerun skip detection
  - US-AUTO-31 handles mandatory analyze gating
  - US-AUTO-58 handles repeated stage-loop escalation
  - US-AUTO-30 and US-AUTO-60 handle safe reuse and lightweight refresh later :contentReference[oaicite:10]{index=10}

## Risks
- If sameness detection is too weak, the story provides little value.
- If sameness detection is too aggressive, the script may block a useful rerun.
- If the implementation reads stale or invalid run evidence, the skip decision could become unsafe.
- If the code drifts into analyze enforcement or review reuse, scope will no longer be atomic.
- The story must therefore use a conservative proof rule and fall back to ordinary run behavior whenever proof is incomplete.

## Acceptance Notes
- The safest interpretation of “would not change the effective review surface” is the narrow one: skip only when existing committed-head evidence already demonstrates sameness for the current committed state.
- The skip path must be explicit and observable in console output.
- The ordinary path must remain available when proof does not exist.
- Registry logic after bundle preparation:
  - `US-AUTO-57` should be treated as `Bundle Drafted`
  - `US-AUTO-56` remains `Implemented`
  - no new follow-up story is required to keep this story atomic

