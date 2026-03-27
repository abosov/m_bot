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

