# US-AUTO-24 PROMPT 1 — Durable Ledger Workflow Redesign

## Role
You are the System Architect + Workflow Designer + Tech Writer for Zumbot.

## Task
Create a design-only follow-up bundle that resolves the durable ledger workflow contradiction introduced by the current `US-AUTO-23` runtime contract.

## Task Intent
Declare this exact sentence before making changes: `Design the workflow-safe durable ledger contract that keeps ledger evidence, clean-tree enforcement, review artifacts, and finalization semantics consistent.`

## Mandatory Context
Read and follow:
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/US-AUTO-23.bundle.md`
- `automation/bundles/active/US-AUTO-23/00_story.md`
- `automation/bundles/active/US-AUTO-23/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-23/04_review_checklist.md`
- `automation/bundles/active/US-AUTO-24/00_sry.md`
- `automation/bundles/active/US-AUTO-24/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-24/02_file_scope.md`

## Goal
Produce a workflow-compliant design bundle that makes the ledger durability contract internally consistent before any runtime implementation resumes.

## Source of Truth
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/US-AUTO-23.bundle.md`
- `automation/bundles/active/US-AUTO-23/00_story.md`
- `automation/bundles/active/US-AUTO-23/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-24/00_story.md`
- `automation/bundles/active/US-AUTO-24/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-24/02_file_scope.md`

## Required Deliverables
Update only:
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/US-AUTO-24.bundle.md`
- `automation/bundles/active/US-AUTO-24/**`

## Files Allowed To Change
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/US-AUTO-24.bundle.md`
- `automation/bundles/active/US-AUTO-24/00_story.md`
- `automation/bundles/active/US-AUTO-24/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-24/02_file_scope.md`
- `automation/bundles/active/US-AUTO-24/03_master_prompt.md`
- `automation/bundles/active/US-AUTO-24/04_review_checklist.md`
- `automation/bundles/active/US-AUTO-24/05_followups.md`
- `automation/bundles/active/US-AUTO-24/06_manual_actions.md`

## Files Not Allowed To Change
- `automation/run_codex_task.sh`
- `automation/scripts/run_story.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/finalize_story.sh`
- `automation/scripts/story_change_ledger.sh`
- `tests/**`
- `backend/**`
- `frontend/**`
- `database/**`
- `migrations/**`

## Required Design Decisions
The bundle must explicitly define all of the following.

### 1. Canonical Event Model
For each of these events:
- `story_started`
- `review_outcome`
- `story_rejected`
- `story_finalized`

Define:
- producer
- timing
- whether it must be committed before downstream consumption
- whether it belongs to feature-branch state, review state, merge state, or post-merge state

### 2. Durability Contract
Define what “durable evidence” means for Zumbot and choose one workflow-safe mechanism.

### 3. Review Artifact Consistency
Define how review bundles remain valid and never become stale relative to the actual code under review.

### 4. Clean-Tree Boundary
Define how ledger writes interact with clean-tree requirements without allowing arbitrary local ledger edits to bypass hygiene checks.

### 5. Finalization Semantics
Resolve the contradiction created by `story_finalized` being appended after merge/cleanup.

### 6. Operator Workflow
Define what the operator must commit, when, and why.

## Decision Options
Evaluate at least these options in the design:
- feature-branch durability before review
- post-merge durability on `main`
- dedicated follow-up commit after review
- another workflow-safe mechanism if clearly justified

Tundle must state the chosen recommendation and why the other options were rejected.

## Constraints
- Do not implement runtime code changes.
- Do not edit runtime scripts, tests, or production code.
- Keep the ledger evidence-oriented, not a policy engine.
- Do not broaden `US-AUTO-23`; isolate this redesign as the next story.
- Do not leave placeholders in the story bundle.

## Output
Return:
1. changed files summary
2. decision summary
3. dependency statement for `US-AUTO-23`
4. validation performed
5. downstream implementation follow-ups that remain out of scope
