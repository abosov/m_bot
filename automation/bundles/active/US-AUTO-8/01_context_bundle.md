# US-AUTO-8 Context Bundle

## Why this story exists

The current AI-dev workflow already has:

- story bundles
- implementation runs
- review preparation
- AI review
- classification
- stable review evidence from commit range

But implementation still happens directly inside the operator's main working tree.

That is the next major instability in the pipeline.

## Observed operational risks

When Codex writes directly into the main working tree:

- failed runs can leave partially applied edits
- repeated runs may depend on manual cleanup
- review can accidentally happen against a mixed state
- troubleshooting becomes harder
- operator confidence drops because the repo may become unexpectedly dirty

## Architectural intent

Implementation execution should be isolated from operator state.

The run should behave more like a disposable execution environment:

- start from a known HEAD
- execute in a temporary worktree
- collect artifacts
- either preserve explicit outputs or cleanly discard temporary execution state

## Preferred direction

Use `git worktree` for run isolation.

High-level shape:

- validate clean primary working tree before run
- create temp worktree rooted at current branch HEAD
- run Codex in that worktree
- collect outputs/artifacts
- clean up worktree
- keep audit trail in the main automation runs directory

## Constraints

- keep patch minimal
- do not redesign the whole pipeline
- do not change product runtime code
- do not change DB or deployment behavior
- preserve existing story/run artifact structure

## Expected result

A Codex implementation run becomes isolated, rerunnable, and much safer to operate.
