## Required Human Actions
1. Create a feature branch for `US-AUTO-54` from current `main`.
2. Save this bundle to `automation/bundle_packs/US-AUTO-54.bundle.md`.
3. Materialize the story bundle:
   - `automation/scripts/materialize_story_bundle.sh US-AUTO-54`
4. Validate the materialized bundle:
   - `automation/scripts/validate_story_bundle.sh US-AUTO-54`
5. Update `docs/90_codex/epics/US-AUTO_REGISTRY.md` so `US-AUTO-54` reflects `Bundle Drafted` or `In Progress`, consistent with the actual execution point.
6. Commit story artifacts before running implementation:
   - bundle pack
   - active bundle files
   - registry update
7. Run the story:
   - `automation/scripts/run_story.sh US-AUTO-54`
8. Analyze the pinned run from the fresh current-HEAD run:
   - `automation/scripts/analyze_story_run.sh US-AUTO-54`
9. Review the result and continue through the normal PR flow only if the run corresponds to current HEAD and the scope stayed narrow.

Recommended local file-open commands:
- `open -a "Cursor" automation/bundle_packs/US-AUTO-54.bundle.md`
- `open -a "Cursor" automation/bundles/active/US-AUTO-54`
- `open -a "Cursor" docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Completion Status
- Story selection: complete
- Atomicity check: complete
- Risk and blast-radius assessment: complete
- Registry logic decision: complete
- Bundle pack assembly: complete
- Internal scope synchronization check (`02_file_scope.md` vs `03_master_prompt.md`): complete
- Sanity check for required headings and seven-section contract: complete
- Ready for materialize + validate: yes
