# US-AUTO-24: Review Checklist

## Scope Validation
- [ ] Changes stay inside `02_file_scope.md`
- [ ] Story remains design-only with no runtime implementation edits
- [ ] The bundle does not broaden `US-AUTO-23`
- [ ] No placeholders remain in bundle content

## Functional Validation
- [ ] The bundle includes a problem statement, architecture constraints, explicit decision options, and a chosen recommendation
- [ ] Canonical event definitions exist for `story_started`, `review_outcome`, `story_rejected`, and `story_finalized`
- [ ] The durability contract defines exactly what counts as durable evidence
- [ ] Review artifact consistency rules prevent stale review bundles
- [ ] Clean-tree rules distinguish expected workflow ledger writes from arbitrary local ledger edits
- [ ] Finalization semantics resolve the post-merge contradiction around `story_finalized`
- [ ] Operator workflow states what must be committed, when, and why
- [ ] Manual actions are present for any required human validation

## Decision Validation
- [ ] Each event specifies producer, timing, commit requirement, and workflow state ownership
- [ ] The bundle compares explicit design options and chooses one recommendation
- [ ] Rejected options are explained, not merely listed
- [ ] Dependency on `US-AUTO-23` is explicit

## Verification
- [ ] File scope is limited to registry + new story bundle files
- [ ] Bundle validation passes
- [ ] The design is suitable as a prerequisite for future implementation work
- [ ] Anti-cycle enforcement is explicitly deferred until this redesign is adopted
