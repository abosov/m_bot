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

