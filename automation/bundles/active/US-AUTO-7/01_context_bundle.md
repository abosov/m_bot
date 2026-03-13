# US-AUTO-7 Context Bundle

## Why this story exists

US-AUTO-6 introduced AI review classification, but post-merge remediation showed that the underlying review evidence could be inconsistent.

The issue is not in the classification logic itself.
The issue is that workflow evidence is currently too dependent on post-run working tree state.

That makes later review/gate steps unstable after implementation has already been committed.

## Observed failure mode

A story can already be committed and present in branch history, but a new review run may still generate:

- empty `changed_files.txt`
- empty `diff.patch`
- `changed_files_detected: no`
- inconsistent review bundle evidence

That leads to false blockers and weakens trust in the automation pipeline.

## Architectural intent

Review evidence should reflect a stable diff source.

The pipeline should be able to answer:

- what changed in this story branch
- what files belong to the reviewable diff
- what patch is being reviewed

even if the working tree is clean at the moment of the run.

## Likely source of defect

The current review artifact generation appears to rely on working-tree diff state after Codex execution.

That is not durable enough for a workflow where implementation is committed before final review/gate runs.

## Desired remediation direction

Use a stable git diff source for review evidence.

Preferred principle:

- implementation may still happen in working tree during Codex execution
- but review artifacts must be generated from a reproducible commit-range diff source suitable for audit and re-review

## Constraints

- keep patch minimal
- do not redesign the whole automation system
- do not touch product runtime code
- do not change DB or deployment behavior
- keep workflow atomic and scriptable

## Expected result

After remediation, a committed story branch should still produce correct review evidence and should not falsely classify itself as having no changed files.
