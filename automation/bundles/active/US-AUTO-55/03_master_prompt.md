# Master Prompt

## Role
You are the implementation engineer for US-AUTO-55 working inside the fail-closed Codex automation pipeline.

## Goal
Implement a narrow fix so downstream review stages handle the exact allowed manual-finish continuation path with compliant final-HEAD semantics after `blocked_non_converging_rerun`, while preserving all ordinary committed-head review rules and rejecting any unproven stale or ambiguous lineage.

## Source of Truth
- docs/90_codex/epics/US-AUTO_REGISTRY.md
- automation/scripts/*
- tests/*

## Files Allowed To Change
(same as 02_file_scope.md)

## Files Not Allowed To Change
(same as 02_file_scope.md)

## Atomic Task Isolation Contract
Only fix manual-finish compliance

## Execution Gate
Stop if orchestration changes required

## Implementation Requirements
- deterministic evidence
- fail-closed
- no fallback

## Verification Requirements
- pytest
- allow + reject cases

## Output
- minimal changes
- focused tests

