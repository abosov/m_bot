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
- Update bundle bootstrap/template behavior to use a canonical unresolved placeholder token instead of loose human placeholders.
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
- The templates contain unresolved human placeholders and default filler text.
- `run_story.sh` checks mostly presence of files, not whether the bundle is materially complete.
- CI already rejects the `_!_` placeholder token, but current templates do not consistently use that canonical unresolved marker.

## Target Outcome
- One bundle pack file can materialize the full seven-file story bundle in one action.
- The bundle is validated before execution.
- Unresolved placeholders or structurally incomplete bundle files cause explicit failure.
- `run_story.sh` refuses to execute a story with an invalid bundle.
