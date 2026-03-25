# Review Checklist

## Scope Validation
- Verify the patch stays within escalation detection and explicit operator resolution.
- Verify the patch does not absorb US-AUTO-25 or US-AUTO-26.
- Verify no unrelated automation refactors are included.
- Verify file changes stay within the allowed scope.

## Functional Validation
- Verify escalation is triggered only by documented deterministic conditions.
- Verify ordinary one-off rejects still behave as ordinary rejects.
- Verify escalation does not silently approve or merge anything.
- Verify the implementation remains fail-closed.
- Verify the operator has a clear explicit command to resolve escalation.
- Verify supported actions are documented:
  - accept-as-is
  - force-followup
  - abort

## Verification
- Verify escalation state is visible in inspectable artifacts.
- Verify analysis output makes escalation-required state obvious.
- Verify positive trigger tests exist.
- Verify negative / non-trigger tests exist.
- Verify continuation-block tests exist.
- Verify explicit resolution action tests exist.
- Verify docs and epic registry are updated consistently.

