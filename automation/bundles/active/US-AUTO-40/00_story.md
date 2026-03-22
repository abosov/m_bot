## Epic
US-AUTO

## Story
As the automation operator,
I want review artifacts to be provably faithful to the actual branch HEAD diff,
so that review and gate decisions are always made against the real code under review rather than a stale or partially matching artifact description.

## Problem / Context
US-AUTO-39 strengthened the gate invariant by binding approval to the reviewed HEAD and rejecting stale checkout HEAD mismatches. That closed one important class of review drift.

However, a separate fidelity gap remains:

- review artifacts may describe a change set that does not fully match the current `origin/main...HEAD` diff;
- artifact text can become stale after additional commits, scope edits, or follow-up adjustments;
- review may still pass while relying on artifact content that is only partially faithful to the real branch delta.

This is a workflow integrity problem. Even if HEAD binding is correct, review quality is still degraded if the review inputs are not guaranteed to reflect the actual code under review.

## Goal
Introduce an explicit workflow contract that makes review artifact fidelity to actual HEAD diff enforceable and testable.

The resulting design must ensure that review is grounded in the real branch diff and cannot silently proceed on stale, partial, or misleading artifact descriptions.

## Desired Outcome
Define and implement a deterministic contract for review artifact fidelity such that:

1. the authoritative code delta for review is the actual branch diff against base (`origin/main...HEAD`, or the repo’s equivalent review base contract);
2. review artifacts are either:
   - generated from that diff, or
   - explicitly validated against that diff before review/gate can approve;
3. if artifacts are stale, partial, or inconsistent with the actual diff, the workflow fails closed or returns an explicit reject;
4. documentation and runbook guidance explain how operators keep artifacts aligned with the real reviewed change set.

## Scope
In scope:

- review artifact fidelity contract design;
- detection of mismatch between artifact-declared review scope and actual branch HEAD diff;
- enforcement point(s) in review and/or gate flow;
- tests covering approve/reject behavior for faithful vs stale artifacts;
- documentation updates for the new contract.

Out of scope:

- full redesign of scope-authority model across all bundle files (that belongs to US-AUTO-41);
- runtime hygiene for `automation/story_change_ledger.jsonl` (belongs to US-AUTO-37 / US-AUTO-38);
- broader run-selection redesign beyond fidelity enforcement (belongs to US-AUTO-35).

## Constraints
- Preserve fail-closed workflow behavior.
- Do not weaken the clean-tree / review-gate discipline established by earlier stories.
- Avoid introducing a second competing source of truth for actual review content.
- Keep the design compatible with current bundle-based workflow unless a strictly better contract is documented and implemented.

## Acceptance Criteria
1. The workflow has a documented and implemented definition of what counts as the authoritative diff for review.
2. Review/gate no longer approves when review artifacts are stale or materially inconsistent with the actual `origin/main...HEAD` diff.
3. Faithful artifacts still allow normal review approval flow.
4. Automated tests cover at least:
   - faithful artifact → approve path;
   - stale or incomplete