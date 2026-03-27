# US-AUTO-46: Manual Actions

## Required Human Actions
- Materialize the bundle with `automation/scripts/materialize_story_bundle.sh US-AUTO-46`.
- Validate the active bundle with `automation/scripts/validate_story_bundle.sh automation/bundles/active/US-AUTO-46`.
- Review the materialized prompt and file scope before execution.
- After implementation, run the focused review-story test targets touched by this change.
- Inspect the blocked-path message manually to confirm it tells the operator how to restore committed-HEAD fidelity before review.

## Execution Notes
- Preferred verification path:
  - validate the bundle;
  - run the story on the feature branch;
  - inspect the blocked review path manually;
  - confirm the clean review path still works as expected.
- This story should not be considered complete if the committed-HEAD guard exists only in theory and has not been exercised through at least one realistic blocked-path verification.

## Completion Status
- [ ] No manual actions required
- [ ] Manual actions completed and documented

## Additional Manual Verification
- Confirm review/classify/gate messaging stays aligned with committed repository state semantics.
