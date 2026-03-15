# US-AUTO-16: AI Review Gate

## Story ID and Title
- Story ID: `US-AUTO-16`
- Title: `AI Review Gate`

## Objective
Create a dedicated AI review gate orchestration step that turns the existing AI review + classification flow into a single machine-readable gate result for a story run.

## Scope
- Add one orchestration script for the latest run of a story.
- Reuse existing `ai_review_story_run.sh` and `classify_review_story_run.sh`.
- Produce a machine-readable gate result artifact with an explicit final decision.
- Document the gate artifact and workflow at a minimal level required for operation.

## Non-goals
- Do not integrate the gate into `finalize_story.sh` yet.
- Do not change merge policy in GitHub.
- Do not redesign the AI review prompt format.
- Do not redesign classification rules.
- Do not refactor existing run artifact generation beyond what is required for the gate.

## Dependencies
- `US-AUTO-8` isolated Codex worktree flow already exists.
- `US-AUTO-11` repository map injection already exists.
- `US-AUTO-13` story finalization script already exists.
- `US-AUTO-14` allowed files guard already exists.
- `US-AUTO-15` finalize checks fallback already exists.

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/REVIEW_CLASSIFICATION_RULES.md`

## Current Code Reality
- `automation/run_codex_task.sh` already generates review artifacts for each run.
- `automation/scripts/ai_review_story_run.sh` already executes AI review for the latest story run.
- `automation/scripts/classify_review_story_run.sh` already classifies AI review findings and writes a classification artifact.
- `automation/scripts/review_story_run.sh` currently only prints a summary of review artifacts.
- There is no single gate orchestration step that produces a final machine-readable `approve/reject` result for downstream automation.

## Target Outcome
After a story run, one script can be executed for a story ID to:
1. run AI review,
2. run review classification,
3. derive final gate decision,
4. write a stable gate result artifact,
5. fail closed when the gate rejects merge.

## Allowed Files
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/templates/review_prompt_template.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`

## Forbidden Files
- `automation/scripts/finalize_story.sh`
- `automation/run_codex_task.sh`
- `automation/scripts/check_allowed_files.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- any backend application code outside the automation/docs scope

## Risks
- Incorrect parsing of classification output could make the gate unreliable.
- Over-scoping into merge/finalize integration would violate atomic delivery.
- Weak output contract would make future automation brittle.

## Manual Actions
- Run the new gate script on a completed story run.
- Verify the gate artifact contains an explicit decision.
- Verify reject/approve behavior matches the classification result.

## Acceptance Notes
- A new orchestration script exists for AI review gating.
- The script writes a durable artifact for the latest story run.
- The artifact includes an explicit gate decision (`approve` or `reject`).
- The script exits non-zero on reject or missing/invalid gate output.
- Existing review/classification flow remains reusable and minimally changed.

