# US-AUTO-37: Ephemeral automation paths contract

## Story ID and Title
- Story ID: `US-AUTO-37`
- Title: `Ephemeral automation paths contract`

## Objective
Define and implement a safe workflow contract for ephemeral automation-generated paths, starting with `automation/story_change_ledger.jsonl`, so this runtime side effect is not treated as normal implementation diff.

## Scope
- Classify `automation/story_change_ledger.jsonl` as an ephemeral automation artifact.
- Align happy-path behavior for `automation/scripts/run_story.sh`.
- Align happy-path behavior for `automation/scripts/finalize_story.sh`.
- Ensure scope-related validation does not treat this path as implementation drift.
- Update focused tests and workflow docs only as needed to support this contract.

## Non-goals
- Do not redesign the durable ledger architecture.
- Do not weaken US-AUTO-39 reviewed-head vs checkout-head invariants.
- Do not weaken US-AUTO-40 artifact fidelity checks.
- Do not change unrelated product, backend, frontend, database, or migration code.
- Do not introduce broad ignore rules that could hide real implementation changes.

## Dependencies
- US-AUTO-39 — reviewed_head vs checkout_head invariant.
- US-AUTO-40 — review artifact fidelity to actual HEAD diff.
- Existing automation workflow scripts for run, review, and finalize.
- Existing bundle validation and execution workflow.

## Source of Truth
- `automation/scripts/run_story.sh`
- `automation/scripts/finalize_story.sh`
- `automation/run_codex_task.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`

## Current Code Reality
- `automation/story_change_ledger.jsonl` is generated as a workflow side effect.
- After `run_story.sh` and after `finalize_story.sh`, this file can leave the working tree dirty.
- The operator currently has to run `git restore automation/story_change_ledger.jsonl` as manual cleanup.
- This creates workflow noise for clean-tree discipline and scope interpretation.

## Target Outcome
- `automation/story_change_ledger.jsonl` is treated as an ephemeral automation path rather than normal implementation diff.
- Happy-path `run_story.sh` does not leave the repo dirty only because of this file.
- Happy-path `finalize_story.sh` does not leave the repo dirty only because of this file.
- Scope validation remains strict for real implementation changes.

