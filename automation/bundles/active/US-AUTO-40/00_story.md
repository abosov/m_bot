# US-AUTO-40

## Story ID and Title
US-AUTO-40 — Review artifact fidelity to actual HEAD diff

## Objective
Enforce a workflow contract in which review artifacts used by review/gate are provably faithful to the actual branch diff under review, so approval cannot proceed on stale, partial, or misleading artifact descriptions.

## Non-goals
- Do not redesign the full single-source-of-truth scope model across bundle files; that belongs to US-AUTO-41.
- Do not solve runtime hygiene for `automation/story_change_ledger.jsonl`; that belongs to US-AUTO-37 / US-AUTO-38.
- Do not redesign broader run resolution behavior beyond what is necessary for artifact fidelity enforcement; that belongs to US-AUTO-35.
- Do not broaden into generic preflight hygiene redesign; that belongs to US-AUTO-36.

## Dependencies
- US-AUTO-39 — HEAD-bound finalized post-commit re-review / re-gate
- Existing review/gate workflow under `automation/scripts/review_story_run.sh` and `automation/scripts/review_gate_story_run.sh`

## Source of Truth
- Actual repository diff for review must be derived from the real branch state against base, normally `origin/main...HEAD` unless the existing workflow already defines a tighter equivalent.
- The current repository scripts, tests, and docs in scope are the authoritative implementation baseline.
- The active bundle for US-AUTO-40 must reflect the implemented contract after the story is completed.

## Current Code Reality
US-AUTO-39 strengthened review/gate by binding decisions to reviewed HEAD and rejecting checkout HEAD mismatches fail-closed.

However, review artifacts can still drift from the real branch diff:
- artifact prose or declared review scope may describe an earlier branch state;
- follow-up commits can change HEAD after artifacts were prepared;
- partial artifact refresh can leave review operating on a stale or incomplete description of the code under review.

This means HEAD identity can be correct while artifact fidelity is still wrong.

## Target Outcome
The workflow must enforce a deterministic artifact-fidelity contract such that:
- the authoritative code delta for review is the actual branch diff;
- review artifacts are generated from or validated against that diff;
- stale or materially inconsistent artifacts are rejected fail-closed;
- faithful artifacts continue to allow normal review approval;
- docs and tests clearly describe and verify the invariant.

## Scope
In scope:
- enforce artifact fidelity between review artifacts and actual branch diff;
- implement focused review/gate checks for stale or incomplete artifact state;
- add or update targeted tests for approve and reject paths;
- update focused operator documentation and active bundle files to reflect the contract.

Out of scope:
- full single-source-of-truth redesign for bundle scope files;
- ledger runtime hygiene or rollback automation;
- broader run-resolution redesign;
- generic preflight hygiene redesign.

## Notes
This story should remain tightly scoped to artifact fidelity enforcement and operator clarity.