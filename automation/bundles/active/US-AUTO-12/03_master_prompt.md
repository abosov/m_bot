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

