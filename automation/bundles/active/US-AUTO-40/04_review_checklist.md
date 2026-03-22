# Review Checklist — US-AUTO-40

## Story intent
Confirm that review artifacts remain faithful to the actual branch HEAD diff and that stale / incomplete artifact state is rejected fail-closed.

## Architecture / contract checks

- Is there now a clearly defined authoritative diff for review?
- Is that diff tied to real repository state rather than only prose artifacts?
- Does the workflow avoid introducing a second competing source of truth?
- Is fidity enforcement scoped specifically to artifact-vs-diff integrity?

## Enforcement checks

- Does review and/or gate detect when review artifacts no longer match actual branch delta?
- Is the mismatch outcome fail-closed or explicit reject?
- Is the failure reason operator-visible and actionable?
- Does US-AUTO-39 HEAD-binding behavior remain intact?

## Fidelity checks

- If new commits are added after review artifacts were prepared, does the workflow reject stale artifacts?
- If actual changed files are missing from review-declared scope, does the workflow reject?
- If artifacts are faithful to actual diff, does normal approval remain possible?

## Test checks

- Are there automated tests for the success path?
- Are there automated tests for stale / incomplete / mismatching artifact reject path?
- Are failure conditions deterministic rather than best-effort?

## Documentation checks

- Do docs explain the fidelity invariant?
- Do docs explain when operator must refresh / rerun review?
- Do docs explain why stale artifact descriptions are no longer acceptable?

## Safety / regression checks

- Does the solution avoid weakening existing clean-tree discipline?
- Does the solution avoid solving unrelated backlog items in this same diff?
- Is the blast radius appropriately small for the story goal?
