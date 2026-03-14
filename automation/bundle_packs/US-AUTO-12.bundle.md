# Story Bundle Pack
Story-ID: US-AUTO-12
Version: 1

=== FILE: 00_story.md ===
# US-AUTO-12: Bundle Pack Materialization & Validation

## Story ID and Title
- Story ID: `US-AUTO-12`
- Title: `Bundle Pack Materialization & Validation`

## Objective
Introduce a single-source bundle pack format plus materialization and validation scripts so a story bundle can be created in one action, validated before execution, and rejected if unresolved placeholders or incomplete sections remain.

## Scope
- Add a single-file bundle pack source format under `automation/bundle_packs/`.
- Add `automation/scripts/materialize_story_bundle.sh`.
- Add `automation/scripts/validate_story_bundle.sh`.
- Update `automation/scripts/run_story.sh` so story execution requires successful bundle validation.
- Update bundle bootstrap/template behavior to use one canonical unresolved placeholder token.
- Add focused tests for materialization and validation behavior.
- Update docs/checklists/specs for the new production bundle workflow.

## Non-goals
- Do not implement PR finalization / merge automation.
- Do not implement allowed-files guard.
- Do not implement AI review gate.
- Do not change `automation/run_codex_task.sh` behavior.
- Do not redesign the whole runner pipeline.

## Dependencies
- Existing story bundle workflow.
- Existing `automation/scripts/new_story_bundle.sh`.
- Existing `automation/scripts/run_story.sh`.
- Existing placeholder CI guard.

## Source of Truth
- `automation/scripts/new_story_bundle.sh`
- `automation/scripts/run_story.sh`
- `automation/templates/story_bundle_template.md`
- `automation/templates/codex_master_prompt_template.md`
- `automation/templates/followup_prompt_template.md`
- `automation/templates/review_prompt_template.md`
- `automation/templates/pr_description_template.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `.github/workflows/no-placeholder-paths.yml`

## Current Code Reality
- Bundle creation is currently bootstrap-oriented: `new_story_bundle.sh` writes seven files from templates immediately.
- Templates contain unresolved guidance placeholders that are not canonical.
- `run_story.sh` checks file presence but not semantic completeness.

## Target Outcome
- One bundle pack file can materialize the full seven-file story bundle in one action.
- Bundle validation rejects unresolved placeholders and incomplete structure.
- `run_story.sh` refuses to execute a story with an invalid bundle.

## Allowed Files
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/scripts/run_story.sh`
- `automation/scripts/new_story_bundle.sh`
- `automation/templates/story_bundle_template.md`
- `automation/templates/codex_master_prompt_template.md`
- `automation/templates/followup_prompt_template.md`
- `automation/templates/review_prompt_template.md`
- `automation/templates/pr_description_template.md`
- `automation/bundle_packs/**`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `tests/test_story_bundle_scripts.py`
- `automation/bundles/active/US-AUTO-12/**`

## Forbidden Files
- `automation/run_codex_task.sh`
- `backend/**`
- `frontend/**`
- `database/**`
- `migrations/**`

## Risks
- Overbuilding parser/templating behavior beyond deterministic needs.
- Partial replacement of active bundles if materialization is not atomic.

## Manual Actions
- Review materialized bundle output for readability and completeness.

## Acceptance Notes
- Materialization must create all seven files.
- Validation must fail on unresolved placeholders and missing required sections.
- `run_story.sh` must block invalid bundles.

=== FILE: 01_context_bundle.md ===
# US-AUTO-12: Context Bundle

## Source of Truth
- `automation/scripts/new_story_bundle.sh`
- `automation/scripts/run_story.sh`
- `automation/templates/story_bundle_template.md`
- `automation/templates/codex_master_prompt_template.md`
- `automation/templates/followup_prompt_template.md`
- `automation/templates/review_prompt_template.md`
- `automation/templates/pr_description_template.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `.github/workflows/no-placeholder-paths.yml`

## Current Code Reality
- `new_story_bundle.sh` currently creates a seven-file bundle directly from templates.
- `run_story.sh` currently checks file presence and then executes the runner.
- There is no bundle pack source file and no pre-run semantic validation.

## Architectural Intent
- Treat one bundle pack file as the canonical source of truth for each story.
- Materialize bundle files atomically from that single source.
- Validate required sections and unresolved placeholders before execution.

## Risks
- Existing manually created bundles may fail new validation until normalized.

## Acceptance Notes
- Materialization and validation are deterministic and script-driven.

=== FILE: 02_file_scope.md ===
# US-AUTO-12: File Scope

## Files Allowed To Change
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/scripts/run_story.sh`
- `automation/scripts/new_story_bundle.sh`
- `automation/templates/story_bundle_template.md`
- `automation/templates/codex_master_prompt_template.md`
- `automation/templates/followup_prompt_template.md`
- `automation/templates/review_prompt_template.md`
- `automation/templates/pr_description_template.md`
- `automation/bundle_packs/**`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `tests/test_story_bundle_scripts.py`
- `automation/bundles/active/US-AUTO-12/**`

## Files Not Allowed To Change
- `automation/run_codex_task.sh`
- `backend/**`
- `frontend/**`
- `database/**`
- `migrations/**`

## Scope Notes
- Keep parser and validator deterministic.
- Keep bootstrap and execution flow explicit.

=== FILE: 03_master_prompt.md ===
# US-AUTO-12 PROMPT 1 — Bundle Pack Materialization & Validation

## Role
You are the Zumbot workflow automation engineer working under the repository's CODEX Operating System.

## Story
US-AUTO-12 — Bundle Pack Materialization & Validation.

## Goal
Introduce a single-source bundle pack format plus materialization and validation scripts so a story bundle can be created in one action, validated before execution, and rejected if unresolved placeholders or incomplete sections remain.

## Source of Truth
- `automation/scripts/new_story_bundle.sh`
- `automation/scripts/run_story.sh`
- `automation/templates/story_bundle_template.md`
- `automation/templates/codex_master_prompt_template.md`
- `automation/templates/followup_prompt_template.md`
- `automation/templates/review_prompt_template.md`
- `automation/templates/pr_description_template.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `.github/workflows/no-placeholder-paths.yml`

## Files Allowed To Change
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/scripts/run_story.sh`
- `automation/scripts/new_story_bundle.sh`
- `automation/templates/story_bundle_template.md`
- `automation/templates/codex_master_prompt_template.md`
- `automation/templates/followup_prompt_template.md`
- `automation/templates/review_prompt_template.md`
- `automation/templates/pr_description_template.md`
- `automation/bundle_packs/**`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `tests/test_story_bundle_scripts.py`
- `automation/bundles/active/US-AUTO-12/**`

## Files Not Allowed To Change
- `automation/run_codex_task.sh`
- `backend/**`
- `frontend/**`
- `database/**`
- `migrations/**`
- finalize-story / merge automation
- allowed-files guard
- AI review gate

## Implementation Requirements
1. Add a canonical bundle pack file format stored under `automation/bundle_packs/`.
2. Add a materialization script that expands one pack into the seven required bundle files.
3. Add a validation script that rejects:
   - missing required files
   - empty files
   - unresolved canonical placeholder tokens
   - missing core required sections in bundle files
4. Make materialization atomic: parse and validate before replacing the active bundle directory.
5. Update `run_story.sh` so successful validation is required before execution.
6. Update bootstrap/template behavior so unresolved sections use one canonical placeholder token already compatible with CI placeholder checks.
7. Keep the design simple and deterministic.

## Testing
Add or update focused tests that verify:
- bundle pack materialization creates the seven required files
- validation fails on unresolved placeholders
- validation fails on structurally incomplete bundles
- `run_story.sh` refuses invalid bundles

## Documentation
Update bundle workflow docs/specs to describe:
- bundle pack as source of truth
- materialize step
- validate step
- bootstrap-only role of `new_story_bundle.sh`

## Output
Return:
1. changed files summary
2. design rationale
3. validation performed
4. risks / follow-ups
5. final diff

=== FILE: 04_review_checklist.md ===
# US-AUTO-12: Review Checklist

## Scope Validation
- [ ] Changes stay inside `02_file_scope.md`
- [ ] No finalize-story automation was added
- [ ] No allowed-files guard logic was added
- [ ] No AI review gate logic was added
- [ ] No unrelated runner refactor was introduced

## Functional Validation
- [ ] One bundle pack can materialize the seven required bundle files
- [ ] Materialization is atomic
- [ ] Validation fails on unresolved placeholders
- [ ] Validation fails on incomplete required sections
- [ ] `run_story.sh` refuses invalid bundles

## Architecture Validation
- [ ] Bundle pack format is simple and deterministic
- [ ] Bootstrap and production flows are clearly separated
- [ ] Canonical unresolved placeholder token is consistent with existing CI policy

## Verification
- [ ] Focused tests updated
- [ ] Docs/specs updated
- [ ] Follow-ups captured separately

=== FILE: 05_followups.md ===
# US-AUTO-12: Follow-Ups

## Follow-Up Prompt Queue
- `US-AUTO-13` — Story Finalization Script
- `US-AUTO-14` — Allowed Files Guard
- `US-AUTO-15` — AI Review Gate

## Iteration Notes
- Keep this story scoped to pack materialization and validation only.
- Defer merge workflow and policy gates to separate stories.

=== FILE: 06_manual_actions.md ===
# US-AUTO-12: Manual Actions

## Required Human Actions
- Review the bundle pack for readability and maintainability.
- Run materialization and inspect generated files.
- Confirm validation and runner gating behavior.

## Execution Notes
- Bootstrap output must be resolved before materialization and execution.

## Completion Status
- [ ] No manual actions required
- [ ] Manual actions completed and documented
