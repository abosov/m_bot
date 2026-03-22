# Context Bundle — US-AUTO-40

## Story
US-AUTO-40 — Review artifact fidelity to actual HEAD diff

## Why this story exists
US-AUTO-39 closed one major integrity gap by making gate evaluation HEAD-bound:

- review/gate now records the reviewed HEAD;
- gate compares reviewed HEAD with current checkout HEAD;
- mismatch is rejected fail-closed.

That solved the problem of approving the wrong checkout state.

A separate problem remains open:

- review artifacts may still describe a change set that is not fully faithful to the actual branch diff;
- artifact text can become stale after follow-up commits or partial bundle updates;
- review can therefore operate using an outdated or incomplete representation of what is actually in `HEAD`.

## Confirmed workflow risk
The current workflow can still drift in the following way:

1. bundle / review artifacts are created for an earlier branch state;
2. additional commits or scope adjustmentspen;
3. review artifacts are only partially updated, or not updated at all;
4. review/gate still evaluates with artifact inputs that no longer faithfully represent `origin/main...HEAD`.

Even with correct HEAD-binding, this creates review-quality drift because the narrative under review is no longer guaranteed to match the real technical delta.

## Core integrity principle for this story
The actual branch diff is the only authoritative technical reality for review.

Review artifacts are allowed only if they remain faithful to that actual diff.
If they materially drift, workflow must reject or fail closed.

## What this story should produce
This story should define and implement a machine-enforceable fidelity contract that answers:

- what exact diff is authoritative for review;
- which artifact(s) declare or summarize reviewed scope;
- how that artifact state is compared against actual git state;
- where the workflow rejects stale / partial / misleading artifact state;
- what the operator must do to recover.

## What this story should not try to solve
This story should stay narrow.

It should **not** fully redesign bundle scope authority across all files.
That broader contract cleanup belongs to **US-AUTO-41**.

It should also **not** solve runtime ledger hygiene or automatic rollback after failed runs.
Those belong to **US-AUTO-37** and **US-AUTO-38**.

## Likely implementation direction
The preferred solution is to enforce fidelity using machine-verifiable repository state rather than trusting free-form narrative text.

Good implementation directions may include:

- deriving reviewed file set from actual git diff;
- comparing declared reviewed scope against actual changed file set;
- rejecting when actual changed files are missing from review-declared scope;
- rejecting when artifacts are stale relative to current HEAD.

## Expected operator outcome
After this story:

- review artifacts should not silently drift from actual code under review;
- operators should get a clear failure reason when artifacts no longer match HEAD;
- rerunning or refreshing review should become the obvious remediation path.

## Dependencies / sequence
This story logically comes after:

- US-AUTO-39 — HEAD-bound finalized post-commit re-review / re-gate

This story should come before:

- US-AUTO-41 — single source of truth for scope contract
- US-AUTO-37 — ephemeral automation paths contract
- US-AUTO-38 — automatic rollback after failed automation run

## Operational reminder
Until the ledger side-effect stories are implemented, after any run:

- check `git status --short`
- if the only dirt is `M automation/story_change_ledger.jsonl`
- run `git restore automation/story_change_ledger.jsonl`
