# US-AUTO-47 — Rerun convergence / manual finish contract

## Story ID and Title
- **Story ID:** US-AUTO-47
- **Title:** Rerun convergence / manual finish contract

## Objective
Introduce a deterministic, fail-closed workflow boundary that detects non-converging committed-head rerun patterns and routes execution into an explicit manual-finish path instead of allowing blind rerun loops.

## Scope
In scope:
- Detect non-converging committed-head rerun pattern:
  - rerun executed after committed HEAD
  - fresh workspace-only changes reappear
  - no stable fixed point is reached
- Introduce deterministic boundary:
  - fixed point → continue
  - non-converging → manual-finish
- Block further reruns once boundary is crossed
- Provide deterministic operator guidance
- Update analysis output
- Add focused regression tests

## Non-goals
- No convergence algorithm
- No runner redesign
- No escalation logic (US-AUTO-28)
- No retry/budget logic
- No fallback continuation

## Dependencies
- US-AUTO-41
- US-AUTO-43
- US-AUTO-46

## Source of Truth
- automation/scripts/run_story.sh
- automation/scripts/analyze_story_run.sh
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md
- docs/90_codex/CODEX_OPERATING_SYSTEM.md
- docs/90_codex/epics/US-AUTO_REGISTRY.md

## Current Code Reality
- Committed-head rerun may re-materialize workspace-only changes
- No explicit convergence boundary exists
- Leads to infinite rerun loops
- Confirmed in US-AUTO-43

## Target Outcome
- Clear distinction:
  - converged → proceed
  - non-converging → manual finish
- No blind reruns
- Deterministic operator path

## Atomic Task Isolation Contract
### Single Purpose
Convergence boundary detection and routing

### Intent
Stop non-converging rerun loops and force manual finish

### Out-of-Scope
- convergence engine
- runner redesign
- escalation logic

### Hard Stop
If runner redesign needed → STOP

### Follow-Up Rule
Convergence engine must be separate story

## Risks
- false positive detection
- scope drift
- confusion with escalation

## Manual Actions
- materialize
- validate
- reproduce scenario
- verify behavior

## Acceptance Notes
- No infinite reruns
- Manual finish deterministic
- Fail-closed preserved

