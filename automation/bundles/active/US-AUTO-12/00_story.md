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

