# Story Bundle Pack
Story-ID: US-AUTO-47
Version: 1

=== FILE: 00_story.md ===
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

=== FILE: 01_context_bundle.md ===
# Context Bundle

## Source of Truth
- run_story.sh
- analyze_story_run.sh
- US-AUTO-43 observation

## Current Code Reality
- Rerun may not converge
- Workspace changes reappear
- No boundary defined

## Architectural Intent
- Add boundary, not engine
- Keep fail-closed
- Preserve architecture

## Risks
- overreach
- false detection

## Acceptance Notes
- deterministic state
- explicit boundary

=== FILE: 02_file_scope.md ===
# File Scope

## Files Allowed To Change
- automation/scripts/run_story.sh
- automation/scripts/analyze_story_run.sh
- tests/test_run_story.py
- tests/test_analyze_story_run.py
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md
- docs/90_codex/CODEX_OPERATING_SYSTEM.md
- automation/bundles/active/US-AUTO-47/**
- automation/bundle_packs/US-AUTO-47.bundle.md

## Files Not Allowed To Change
- automation/run_codex_task.sh
- automation/scripts/review_gate_story_run.sh
- automation/scripts/ai_review_story_run.sh
- automation/scripts/classify_review_story_run.sh

## Scope Notes
Allowed:
- detection logic
- boundary classification
- messaging
- tests

Forbidden:
- runner redesign
- retry logic
- orchestration

=== FILE: 03_master_prompt.md ===
# US-AUTO-47 PROMPT 1

## Role
Codex automation engineer

## Goal
Implement convergence boundary

## Source of Truth
- run_story.sh
- analyze_story_run.sh

## Files Allowed To Change
- automation/scripts/run_story.sh
- automation/scripts/analyze_story_run.sh
- tests/test_run_story.py
- tests/test_analyze_story_run.py
- automation/bundles/active/US-AUTO-47/**
- automation/bundle_packs/US-AUTO-47.bundle.md

## Files Not Allowed To Change
- automation/run_codex_task.sh
- automation/scripts/review_gate_story_run.sh

## Atomic Task Isolation Contract
- One purpose only
- Fail closed
- No expansion

## Execution Gate
- STOP if runner touched
- STOP if escalation logic added

## Implementation Requirements
- detect non-converging rerun
- block rerun
- route to manual finish
- deterministic output

## Verification Requirements
- converging works
- non-converging blocked
- manual path shown

## Output
- diff
- explanation
- tests

=== FILE: 04_review_checklist.md ===
# Review Checklist

## Scope Validation
- [ ] only allowed files
- [ ] no runner changes

## Functional Validation
- [ ] rerun works normally
- [ ] loop blocked
- [ ] manual finish shown

## Verification
- [ ] tests pass

## HARD BLOCK
REJECT IF:
- loop still possible
- fallback exists
- scope expanded

=== FILE: 05_followups.md ===
# Follow-Ups

## Follow-Up Prompt Queue
- convergence engine (candidate)
- US-AUTO-28
- budget guard

## Iteration Notes
- keep narrow
- no expansion

=== FILE: 06_manual_actions.md ===
# Manual Actions

## Required Human Actions
1. automation/scripts/materialize_story_bundle.sh US-AUTO-47
2. automation/scripts/validate_story_bundle.sh US-AUTO-47
3. update registry
4. create branch
5. commit bundle
6. automation/scripts/run_story.sh US-AUTO-47
7. automation/scripts/analyze_story_run.sh US-AUTO-47

## Completion Status
- [ ] materialized
- [ ] validated
- [ ] executed
- [ ] verified