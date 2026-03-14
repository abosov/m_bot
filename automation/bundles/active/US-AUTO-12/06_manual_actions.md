# US-AUTO-12: Manual Actions

## Required Human Actions
- Review the new bundle pack format for readability and maintainability
- Run materialization for one story pack and inspect the generated seven-file bundle
- Confirm validation fails on unresolved placeholder tokens
- Review final diff before PR

## Suggested Manual Verification
- materialize one story bundle from a pack
- inspect:
  - generated bundle directory
  - validator output
  - `run_story.sh` behavior on invalid bundle
- verify bootstrap templates clearly show canonical unresolved placeholders

## Completion Status
- [ ] Manual verification completed
- [ ] Ready for PR
