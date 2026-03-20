# Story Bundle Pack
Story-ID: US-AUTO-20
Version: 1

This pack is the single source of truth for materialized story bundle files.

=== FILE: 00_story.md ===
# US-AUTO-20: Workflow Chaining & Resume

## Story ID and Title
- Story ID: `US-AUTO-20`
- Title: `Workflow Chaining & Resume`

## Objective
Add a deterministic operator workflow helper that reports the latest valid story-run stage, recommends the exact next command, and supports safe resume from existing run artifacts.

## Scope
- Define the canonical stage sequence for the US-AUTO automation workflow after a story run.
- Reuse existing run artifacts to detect the latest valid completed stage.
- Add one operator-facing helper that prints:
  - current run state,
  - latest valid completed stage,
  - next recommended command,
  - blocked/fail-closed reason when continuation is unsafe.
- Support safe resume guidance from the latest valid stage without introducing hidden state.
- Add focused tests for stage detection, stale evidence handling, and next-step recommendation.
- Update the relevant automation docs/checklists for the new chaining/resume behavior.

## Non-goals
- Do not add autonomous execution of the next step.
- Do not redesign `automation/run_codex_task.sh`.
- Do not auto-merge or auto-finalize stories.
- Do not change backend, migrations, website, or product application flows.
- Do not expand this story into the broader operator UX redesign planned separately.

## Dependencies
- Existing run artifact generation in `automation/run_codex_task.sh`.
- Existing workflow stages:
  - `automation/scripts/ai_review_story_run.sh`
  - `automation/scripts/classify_review_story_run.sh`
  - `automation/scripts/review_gate_story_run.sh`
  - `automation/scripts/analyze_story_run.sh`
- Existing governance constraints from:
  - `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
  - `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/run_codex_task.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`

## Current Code Reality
- The pipeline already has separate execution, AI review, classification, gate, and analysis steps.
- The operator still has to remember the correct command sequence manually.
- Resume behavior is implicit and distributed across scripts rather than surfaced as one canonical helper.
- Evidence consistency checks already exist in `analyze_story_run.sh`, but they do not yet provide one explicit chaining/resume command path.

## Target Outcome
- The operator can run one helper command for a story ID.
- The helper reads existing repository evidence.
- The helper identifies the latest valid stage.
- The helper prints the exact next recommended command.
- The helper fails closed when evidence is stale, missing, inconsistent, or unsafe to continue.

## Atomic Task Isolation Contract
- Single purpose: add deterministic chaining/resume guidance for the existing automation pipeline.
- Exact intent: detect the latest valid stage from existing artifacts and print one safe next action.
- Out of scope:
  - backend/product changes,
  - broader console UX redesign,
  - autonomous execution,
  - unrelated workflow refactors.
- Allowed file boundary is defined in this bundle and must be enforced strictly.
- Forbidden file/area boundary is defined in this bundle and must be treated as hard scope limits.
- Hard-stop condition: if implementation requires product-layer changes, hidden state, or broad UX redesign, stop and capture that work as a follow-up instead.
- Newly discovered out-of-scope findings must become follow-up work, not inline expansion.
- Each follow-up prompt must isolate exactly one blocker or one independently reviewable improvement.

## Allowed Files
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/**`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `tests/**`
- `automation/bundle_packs/**`
- `automation/bundles/active/US-AUTO-20/**`

## Forbidden Files
- `backend/**`
- `migrations/**`
- `web/**`
- `admin_api.py`
- `database.py`
- product application flows unrelated to automation
- autonomous/background execution infrastructure

## Risks
- Resume logic may over-assume validity if evidence freshness is not checked strictly.
- Stage vocabulary may become noisy if the implementation tries to expose too many intermediate states.
- Scope could drift into full console UX redesign if boundaries are not enforced.

## Manual Actions
- Human still runs the recommended commands manually.
- Human still reviews output before merge/finalization decisions.

## Acceptance Notes
- The implementation must report current stage and next step from repository evidence.
- Resume guidance must fail closed on stale or inconsistent evidence.
- The implementation must remain inside automation/docs/tests scope.
- The story must improve operator continuity without introducing autonomous execution.

=== FILE: 01_context_bundle.md ===
# US-AUTO-20: Context Bundle

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/run_codex_task.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`

## Current Code Reality
- The repository already supports discrete automation stages:
  - story execution,
  - AI review,
  - review classification,
  - review gate,
  - run analysis.
- The operator still has to infer the next step manually from scattered run artifacts and existing scripts.
- `analyze_story_run.sh` already contains important consistency and staleness checks, so this story should build on that reality rather than inventing a parallel model.

## Architectural Intent
- Add orchestration guidance, not orchestration automation.
- Reuse existing artifacts and stage semantics instead of inventing a new execution model.
- Make the safe next step obvious and deterministic from repository evidence.
- Prefer a small explicit stage model and fail-closed behavior.

## Risks
- The implementation could accidentally duplicate logic already present in run analysis instead of reusing it.
- The workflow helper could become too broad and drift into general operator UX work.
- Resume output could be misleading if it does not clearly distinguish valid evidence from stale evidence.

## Acceptance Notes
- One canonical helper path must exist for “what do I do next?”
- The helper must emit one next recommended action or a blocked reason.
- The helper must support safe resume from the latest valid stage.
- Missing or stale evidence must stop continuation explicitly.

=== FILE: 02_file_scope.md ===
# US-AUTO-20: File Scope

## Files Allowed To Change
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/**`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `tests/**`
- `automation/bundle_packs/**`
- `automation/bundles/active/US-AUTO-20/**`

## Files Not Allowed To Change
- `backend/**`
- `migrations/**`
- `web/**`
- `admin_api.py`
- `database.py`
- product application flows unrelated to automation

## Scope Notes
- Keep chaining/resume logic deterministic and artifact-driven.
- Reuse existing stage semantics where possible.
- Do not expand into broader UX redesign or autonomous execution.

=== FILE: 03_master_prompt.md ===
# US-AUTO-20 PROMPT 1 — Workflow Chaining & Resume

## Role
You are the Zumbot workflow automation engineer working under the repository's CODEX Operating System.

## Goal
Add a deterministic operator workflow helper that reports the latest valid stage of a story run, recommends the exact next command, and supports safe resume from existing run artifacts.

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/run_codex_task.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh
## Files Allowed To Change
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/**`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `tests/**`
- `automation/bundle_packs/**`
- `automation/bundles/active/US-AUTO-20/**`

## Files Not Allowed To Change
- `backend/**`
- `migrations/**`
- `web/**`
- `admin_api.py`
- `database.py`
- product application flows unrelated to automation
- autonomous/background execution infrastructure

## Atomic Task Isolation Contract
- Intent statement: implement only chaining/resume guidance for the existing automation workflow.
- Out of scope: backend changes, broad UX redesign, autonomous execution, unrelated cleanup.
- Atomic Task Isolation is mandatory for this run.
- Before changing files, declare the one-sentence task intent.
- If the task becomes non-atomic, underspecified, or split across multiple independent findings, stop.
- Capture newly discovered out-of-scope findings as follow-up work instead of expanding this run.
- Follow-up prompts are not an exception path around Atomic Task Isolation.

## Output
Return:
1. changed files summary
2. stage model summary
3. validation performed
4. risks / follow-ups
5. final diff

=== FILE: 04_review_checklist.md ===
# US-AUTO-20: Review Checklist

## Scope Validation
- [ ] Changes stay inside `02_file_scope.md`
- [ ] No backend/product files were changed
- [ ] No unrelated refactor or formatting-only edits were introduced
- [ ] Atomic Task Isolation remained explicit and enforced

## Functional Validation
- [ ] Latest valid stage is detected from existing run artifacts
- [ ] Exactly one next recommended action is printed
- [ ] Resume guidance fails closed on stale or inconsistent evidence
- [ ] Existing workflow stages remain reusable and explicit

## Verification
- [ ] Focused tests/validation commands are recorded
- [ ] Manual verification steps are recorded when needed
- [ ] Risks and follow-ups are captured before merge

=== FILE: 05_followups.md ===
# US-AUTO-20: Follow-Ups

## Follow-Up Prompt Queue
- `US-AUTO-23` — add durable per-story change ledger / anti-cycle memory
- `US-AUTO-18` — improve oper-facing UX after chaining/resume is stable

## Iteration Notes
- Keep this story limited to deterministic chaining/resume guidance.
- Do not absorb the broader operator UX redesign into this implementation.

=== FILE: 06_manual_actions.md ===
# US-AUTO-20: Manual Actions

## Required Human Actions
- Materialize the bundle after pack completion.
- Validate the bundle before story execution.
- Run the story on a feature branch.
- Review the helper output against real run artifacts before merge.

## Execution Notes
- Preferred verification path:
  - materialize the bundle,
  - validate the bundle,
  - run one story flow on a feature branch,
  - inspect the reported stage and recommended next action,
  - confirm fail-closed behavior on stale or incomplete evidence.

## Completion Status
- [ ] No manual actions required
- [ ] Manual actions completed and documented
