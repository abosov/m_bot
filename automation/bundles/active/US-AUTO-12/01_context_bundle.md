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
- `new_story_bundle.sh` creates a valid directory structure but not a production-ready bundle.
- Template output includes unresolved placeholders such as `<path>`-style guidance and placeholder prose.
- `run_story.sh` currently validates that required files exist but does not fail on template residue or incomplete story definition.
- The repo already contains a CI guard for placeholder tokens, which can become the canonical unresolved marker for bundle validation.

## Architectural Intent
- Introduce a single source of truth for bundle content: one bundle pack file per story.
- Materialize the seven bundle files from that pack atomically.
- Validate structure and semantic completeness before story execution.
- Keep `new_story_bundle.sh` as bootstrap-only, not the canonical production flow.
- Make bundle validation a hard precondition of `run_story.sh`.

## Minimal Design
- Add `automation/bundle_packs/<STORY_ID>.bundle.md` as the canonical bundle pack format.
- Add a materializer script that parses the pack into the seven bundle files.
- Add a validator script that checks:
  - all seven files exist
  - files are non-empty
  - required sections are present
  - canonical unresolved placeholder token is absent
- Update templates/bootstrap so unresolved sections use one canonical placeholder token that CI already knows how to reject.

## Risks
- Overbuilding a mini templating engine instead of a simple deterministic parser.
- Letting the materializer partially overwrite a bundle on failure.
- Mixing this story with story-finalization or scope-guard work.

## Acceptance Notes
- One command should materialize a full bundle from a pack file.
- Validation must fail clearly on unresolved placeholders or incomplete bundle structure.
- `run_story.sh` must refuse to execute invalid bundles.
