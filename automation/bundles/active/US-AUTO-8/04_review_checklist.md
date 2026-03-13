# US-AUTO-8 Review Checklist

## Scope and architecture
- [ ] Only allowed automation/workflow files changed
- [ ] No product runtime code changed
- [ ] No DB/schema/deployment changes introduced
- [ ] Patch stays minimal and focused on isolated execution

## Functional checks
- [ ] Temporary worktree is created for implementation run
- [ ] Codex executes inside the temporary worktree
- [ ] Primary working tree is not directly mutated by the run
- [ ] Run artifacts are still written to the normal run directory
- [ ] Manifest records isolated-run metadata
- [ ] Temporary worktree cleanup works on success
- [ ] Temporary worktree cleanup works on failure

## Reproducibility
- [ ] Run state is isolated from operator state
- [ ] Rerun behavior is safer than direct main-tree execution
- [ ] Workflow remains deterministic and auditable

## Tests
- [ ] Relevant tests added or updated
- [ ] Isolated worktree lifecycle is covered
- [ ] Cleanup behavior is covered
- [ ] No obvious regression in run workflow

## Manual verification
- [ ] run story execution once and confirm primary working tree stays clean
- [ ] inspect latest run manifest for worktree metadata
- [ ] confirm no orphaned worktree remains after normal completion
