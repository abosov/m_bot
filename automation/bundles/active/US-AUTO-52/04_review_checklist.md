# Review Checklist — US-AUTO-52

## Scope Validation
- APPROVE only if changed files are limited to the allowed scope.
- REJECT if any file outside the allowed list changed.
- REJECT if the story mixes continuation contract tightening with unrelated UX, orchestration, retry, or validator changes.
- REJECT if the registry update claims implementation/closure for US-AUTO-51 instead of recording it as a rejected corrective predecessor.

## Functional Validation
- APPROVE only if the implementation allows continuation for the exact committed manual-finish case tied to the blocked run evidence.
- REJECT if continuation is still allowed for any ancestor-of-HEAD generalization.
- REJECT if continuation is allowed for descendant commits after the manual-finish commit.
- REJECT if the valid exact-case continuation path is accidentally disabled.
- REJECT if analyze/classify/gate disagree about the same continuation boundary.

## Verification
- APPROVE only if targeted regression tests prove:
  - exact allowed case passes,
  - descendant case rejects,
  - ancestor-based case rejects.
- REJECT if tests were weakened instead of enforcing the contract.
- REJECT if verification artifacts are stale relative to the commit under review.
- REJECT if review outcome depends on workspace-only changes or non-committed state.

