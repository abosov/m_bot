# Story Bundle Pack
Story-ID: US-AUTO-16
Version: 1

This pack is the single source of truth for materialized story bundle files.

=== FILE: 00_story.md ===
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

=== FILE: 01_context_bundle.md ===
# US-AUTO-16: Context Bundle

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/REVIEW_CLASSIFICATION_RULES.md`

## Current Code Reality
- Review artifacts are already produced in `automation/runs/<STORY_ID>/<RUN_ID>/`.
- AI review already writes `ai_review_result.md`.
- Classification already writes `review_classification.md`.
- No script currently converts these artifacts into a single gate result for downstream automation.
- `finalize_story.sh` is still independent from AI review classification.

## Architectural Intent
Build a narrow review gate layer on top of existing artifacts and scripts:
- orchestrate existing review steps,
- produce one final decision artifact,
- preserve clean boundaries,
- avoid coupling to finalization until a follow-up story.

## Risks
- Free-form LLM output can be ambiguous unless the gate decision is normalized.
- Parsing logic must fail closed if recommendation is absent or malformed.
- Scope creep into finalize/merge blocking must be avoided in this story.

## Acceptance Notes
- One entrypoint script owns review gate orchestration.
- Review result + classification result remain readable artifacts.
- Gate decision is machine-readable and stable for future automation.

=== FILE: 02_file_scope.md ===
# US-AUTO-16: File Scope

## Files Allowed To Change
- `tests/test_review_classification_script.py`
- `tests/test_review_gate_story_run.py`
- `tests/test_run_codex_task.py`
- `automation/bundle_packs/US-AUTO-16.bundle.md`
- `automation/bundles/active/US-AUTO-16/00_story.md`
- `automation/bundles/active/US-AUTO-16/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-16/02_file_scope.md`
- `automation/bundles/active/US-AUTO-16/03_master_prompt.md`
- `automation/bundles/active/US-AUTO-16/04_review_checklist.md`
- `automation/bundles/active/US-AUTO-16/05_followups.md`
- `automation/bundles/active/US-AUTO-16/06_manual_actions.md`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/templates/review_prompt_template.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`

## Files Not Allowed To Change
- `automation/scripts/finalize_story.sh`
- `automation/run_codex_task.sh`
- `automation/scripts/check_allowed_files.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `backend/**`
- `database/**`

## Scope Notes
- Prefer adding `automation/scripts/review_gate_story_run.sh` as the main new file.
- Reuse existing review scripts with minimal edits only if required for a stable gate artifact contract.
- Do not integrate with finalize in this story.

=== FILE: 03_master_prompt.md ===
# US-AUTO-16 PROMPT 1 — AI Review Gate

## Role
You are the System Architect + Data Architect + UX + Developer + Tech Writer + QA + Security Reviewer for Zumbot.

## Task
Implement a narrow AI review gate orchestration flow for story runs. Reuse the existing AI review and review classification scripts, add a single orchestration entrypoint, and produce a machine-readable final gate result artifact with an explicit `approve` or `reject` decision.

## Mandatory Context
Read and follow:
- docs/90_codex/CODEX_OPERATING_SYSTEM.md
- docs/90_codex/PROJECT_CONTEXT.md
- docs/90_codex/REPOSITORY_MAP.md
- docs/90_codex/PROJECT_CONTEXT_UPDATE_PROTOCOL.md
- docs/90_codex/REVIEW_CLASSIFICATION_RULES.md
- automation/bundles/active/US-AUTO-16/00_story.md
- automation/bundles/active/US-AUTO-16/01_context_bundle.md
- automation/bundles/active/US-AUTO-16/02_file_scope.md

## Goal
Create a stable review gate layer that can be called for a story ID and the latest run, writes a finagate result artifact, and exits non-zero if the gate rejects merge or cannot derive a valid decision.

## Non-goals
Do not:
- modify `automation/scripts/finalize_story.sh`
- integrate gate checks into merge/finalize flow
- redesign the LLM review/classification process
- change unrelated automation runner behavior
- add unrelated refactors or formatting-only edits

## Source of Truth
- `docs/90_codex/REVIEW_CLASSIFICATION_RULES.md`
- `automation/bundles/active/US-AUTO-16/00_story.md`
- `automation/bundles/active/US-AUTO-16/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-16/02_file_scope.md`

## Files Allowed To Change
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/templates/review_prompt_template.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`

## Files Not Allowed To Change
- `automation/scripts/finalize_story.sh`
- `automation/run_codex_task.sh`
- `automation/scripts/check_allowed_files.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `backend/**`
- `database/**`

## Implementation Rules
- minimal patch only
- no unrelated refactor
- no formatting-only edits
- update docs only when behavior/process changes require it

## Test Plan
- `pytest tests/test_review_classification_script.py tests/test_review_story_run.py tests/test_run_codex_task.py`

## Output
Return:
1. changed files summary
2. rationale
3. test results
4. risks/follow-ups
5. final diff

=== FILE: 04_review_checklist.md ===
# US-AUTO-16: Review Checklist

## Scope Validation
- [ ] Changes stay inside `02_file_scope.md`
- [ ] Source-of-truth files are complete and resolved
- [ ] No unrelated refactor or formatting-only edits

## Functional Validation
- [ ] A single review gate entrypoint script exists
- [ ] The gate runs AI review and review classification for the latest story run
- [ ] The gate writes a machine-readable result artifact with explicit final decision
- [ ] The gate exits non-zero on reject or invalid/missing decision
- [ ] Existing review artifacts remain available for manual inspection

## Architecture / Source of Truth
- [ ] Source-of-truth docs are listed and followed
- [ ] Architecture boundaries remain intact
- [ ] Finalize/merge integration is not introduced in this story

## Verification
- [ ] Targeted commands/validation steps are recorded
- [ ] Manual verification steps are recorded when needed
- [ ] Risks and follow-ups are captured before merge

## Review Prompt Seed

```md
# US-AUTO-16 REVIEW PROMPT — Implementation Review

## Role
You are the Reviewer (Architect + QA + Security) for Zumbot.

## Review Inputs
- Story bundle: `automation/bundles/active/US-AUTO-16/`
- Code diff: `<RUN ARTIFACT>`
- Test evidence: `<RUN ARTIFACT>`
- Classification rules: `docs/90_codex/REVIEW_CLASSIFICATION_RULES.md`

## Review Task
1. Validate scope against allowed/forbidden files.
2. Validate architecture and source-of-truth compliance.
3. Validate tests for changed behavi.
4. Validate that gate output is stable and fail-closed.
5. Classify each finding:
   - `MERGE BLOCKER`
   - `MINOR IMPROVEMENT`
   - `FOLLOW-UP STORY`

## Output
Return:
1. Findings by severity/classification
2. Required fixes before merge
3. Optional improvements
4. Follow-up stories to create
5. Merge recommendation (`approve` or `reject`)


=== FILE: 05_followups.md ===

US-AUTO-16: Follow-Ups
## Follow-Up Prompt Queue

Integrate AI review gate into finalize_story.sh as a blocking pre-merge condition.

Add dedicated automated tests for review gate parsing and decision handling.

## Iteration Notes

Keep this story limited to creating the gate orchestration and result artifact contract.

Defer finalize integration to the next automation story.

Prefer explicit fail-closed behavior if classification output is ambiguous.

Follow-Up Prompt Template

# US-AUTO-16 FOLLOW-UP PROMPT 1 — <Fix/Adjustment>

## Role
You are the System Architect + Developer + QA + Security Reviewer for Zumbot.

## Context
- Base story bundle: `automation/bundles/active/US-AUTO-16/`
- Previous run output: `automation/output/<story-run-id>/`
- Review checklist: `automation/bundles/active/US-AUTO-16/04_review_checklist.md`

## Target
Fix only the specific review gate issue identified during review without expanding scope into finalize integration or unrelated automation refactors.

## Findings To Address
- <finding>
- <finding>

## Files Allowed To Change
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_sty_run.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/templates/review_prompt_template.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`

## Files Not Allowed To Change
- `automation/scripts/finalize_story.sh`
- `automation/run_codex_task.sh`
- `backend/**`
- `database/**`

## Rules
- keep patch minimal and scoped
- preserve architecture boundaries
- do not introduce new features beyond listed findings

## Tests
- `pytest tests/test_review_classification_script.py tests/test_review_story_run.py tests/test_run_codex_task.py`

## Output
Return:
1. addressed findings
2. changed files summary
3. test results
4. residual risks
5. final diff

PR Description Template

# US-AUTO-16 — AI Review Gate

## Summary
- add a single AI review gate orchestration script
- reuse existing AI review and classification steps
- write a machine-readable gate result artifact with explicit approve/reject status

## Story Context
- Story bundle: `automation/bundles/active/US-AUTO-16/`
- Objective: create a stable gate result r downstream automation
- Non-goals: no finalize integration, no merge-policy changes, no unrelated refactor

## Scope
- review gate orchestration for latest story run
- stable gate result artifact contract
- minimal docs/process update if needed

## Files Changed
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_story_run.sh`
- `automation/templates/review_prompt_template.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`


=== FILE: 06_manual_actions.md ===
# US-AUTO-16: Manual Actions

## Required Human Actions
- Confirm the story bundle materializes and validates successfully.
- Review existing review artifacts flow for the latest story run format.

## Implementation
- Implement the AI review gate entrypoint script within the allowed automation scope only.
- Reuse existing AI review and classification scripts instead of duplicating their logic.

## Verification
- Run `automation/scripts/materialize_story_bundle.sh US-AUTO-16`
- Run `automation/scripts/validate_story_bundle.sh US-AUTO-16`
- Run the new review gate script against a story run that already has review artifacts.
- Verify the gate result artifact contains an explicit `approve` or `reject` decision.
- Verify the script exits non-zero when the decision is reject or cannot be derived.

## Completion Status
- Record any follow-up needed for finalize integration as a separate story.
- Keep merge/finalize integration out of this story.
