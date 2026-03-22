Story-ID: US-AUTO-38
Title: Automatic rollback after failed automation run
Epic: US-AUTO
Status: Draft

=== FILE: 00_story.md ===
# US-AUTO-38: Automatic rollback after failed automation run

## Story ID and Title
- Story ID: `US-AUTO-38`
- Title: `Automatic rollback after failed automation run`

## Objective
Introduce a deterministic automatic rollback contract for automation story runs so that any failed or interrupted run returns the repository working tree to the exact clean pre-run state without manual operator cleanup, while preserving the ephemeral automation paths contract established in US-AUTO-37.

## Scope
- Define the canonical failed-run rollback contract for automation story execution.
- Make rollback apply only when execution starts from a clean tree.
- Centralize rollback lifecycle ownership in the top-level orchestration layer.
- Restore tracked changes to the pre-run baseline on failed execution.
- Clean run-owned untracked artifacts created during failed execution.
- Preserve success behavior so intended story changes remain after a successful run.
- Add focused tests for success, failure, interruption/simulated trap behavior, and rollback-failure surfacing.
- Update workflow docs/checklists so failed-run semantics are explicit and auditable.

## Non-goals
- Do not redesign finalize flow.
- Do not introduce hidden stash-based recovery by default.
- Do not support rollback when the operator starts from a dirty tree.
- Do not redesign the story registry or broader ledger model.
- Do not expand this story into unrelated review gate, deployment, or budget-control work.

## Dependencies
- US-AUTO-37 ephemeral automation paths contract.
- Existing story bundle materialization/validation workflow.
- Existing execution wrappers:
  - `automation/scripts/run_story.sh`
  - `automation/run_codex_task.sh`
- Existing execution docs and checklist flow.

## Source of Truth
- `automation/scripts/run_story.sh`
- `automation/run_codex_task.sh`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- existing tests covering story execution behavior
- merged US-AUTO-37 behavior

## Current Code Reality
- US-AUTO-37 removed a class of false dirty-tree problems caused by ephemeral automation paths.
- Ephemeral cleanup is more consistent, but failed execution can still leave partial repository mutations behind.
- Current failure handling is not yet defined as a deterministic restore-to-baseline contract.
- Success and failure boundaries are not explicit enough for rollback ownership and diagnostics.

## Target Outcome
- Failed automation runs restore the exact clean pre-run repository state automatically.
- Successful runs preserve intended working tree changes.
- Rollback lifecycle ownership is centralized and explicit.
- Interrupted runs are treated as failures where supported.
- US-AUTO-37 behavior remains intact and regression-tested.

## Atomic Task Isolation Contract
- Single purpose: add deterministic automatic rollback for failed automation runs.
- Exact intent: restore the repository to its clean pre-run baseline after any supported failed or interrupted execution path.
- Out of scope:
  - finalize redesign,
  - broader registry/ledger redesign,
  - unrelated review/deploy changes.
- Allowed file boundary is defined in this bundle and must be enforced strictly.
- Forbidden file/area boundary is defined in this bundle and must be treated as a hard stop.
- Hard-stop condition: if implementation requires broader workflow redesign outside failed-run rollback semantics, stop and capture that work as a follow-up.

=== FILE: 01_context_bundle.md ===
# US-AUTO-38: Context Bundle

## Source of Truth
- `automation/scripts/run_story.sh`
- `automation/run_codex_task.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- tests covering story execution and cleanup behavior
- merged US-AUTO-37 workflow behavior

## Current Code Reality
- Ephemeral automation path cleanup is already improved after US-AUTO-37.
- `automation/story_change_ledger.jsonl` no longer drives false dirty-tree behavior in ordinary status/diff semantics.
- A story run may still enter a mutable execution window, fail or be interrupted, and leave partial changes behind.
- Operator cleanup after failed execution is still partially manual and not contractually defined.

## Architectural Intent
Treat story execution like a repository-scoped transaction:
- verify clean entry;
- capture a pre-run baseline;
- arm rollback before mutable execution;
- disarm rollback only at an explicit success boundary;
- on failure/interruption, restore tracked state and clean run-owned untracked artifacts;
- keep diagnostics visible without leaving the repository dirty by default.

Preferred ownership:
- top-level orchestration layer owns repository rollback lifecycle;
- lower-level runners may perform local cleanup but should not own the transaction boundary.

## Risks
- over-broad cleanup could remove more than intended;
- split rollback ownership could cause conflicting cleanup logic;
- rollback might trigger after success if disarm logic is weak;
- diagnostics could be lost if cleanup is too aggressive;
- new rollback behavior could regress US-AUTO-37 ephemeral path handling.

## Acceptance Notes
Accept the story only if:
- failed execution from a clean start restores the exact clean pre-run state;
- success preserves intended changes;
- rollback failure is surfaced loudly;
- regression tests confirm US-AUTO-37 behavior remains intact;
- docs clearly define when rollback applies and what it restores.

=== FILE: 02_file_scope.md ===
# US-AUTO-38: File Scope

## Files Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/run_codex_task.sh`
- `tests/test_run_story*.py`
- `tests/test_run_codex_task*.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `automation/bundle_packs/US-AUTO-38.bundle.md`
- `automation/bundles/active/US-AUTO-38/**`

## Files Not Allowed To Change
- `backend/**`
- `frontend/**`
- `database/**`
- `migrations/**`
- unrelated finalize redesign
- story registry redesign
- unrelated review gate policy
- deployment / VPS runtime behavior
- unrelated budget / loop / escalation stories

=== FILE: 03_master_prompt.md ===
# US-AUTO-38 PROMPT 1 — Automatic rollback after failed automation run

## Role
You are the System Architect, Shell Workflow Engineer, Test Engineer, and Tech Writer for Zumbot.

## Story
US-AUTO-38 — Automatic rollback after failed automation run.

## Goal
Implement a deterministic automatic rollback contract so failed or interrupted automation runs restore the exact clean pre-run repository state, while successful runs preserve intended changes and US-AUTO-37 behavior remains intact.

## Source of Truth
- `automation/scripts/run_story.sh`
- `automation/run_codex_task.sh`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- tests covering story execution behavior
- merged US-AUTO-37 behavior

## Files Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/run_codex_task.sh`
- `tests/test_run_story*.py`
- `tests/test_run_codex_task*.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`

## Files Not Allowed To Change
- `backend/**`
- `frontend/**`
- `database/**`
- `migrations/**`
- unrelated finalize redesign
- story registry redesign
- unrelated review gate policy
- unrelated deployment work

## Implementation Requirements
1. Rollback applies only when execution starts from a clean tree.
2. Top-level orchestration must own rollback lifecycle.
3. Rollback is armed after baseline capture and disarmed only at explicit success boundary.
4. Any failed run path must restore tracked changes and clean run-owned untracked artifacts.
5. Interrupted execution should be treated as failure where supported.
6. Rollback failure must surface loudly and must never masquerade as success.
7. US-AUTO-37 ephemeral path behavior must not regress.

## Guardrails
- Do not broaden cleanup beyond run-owned scope without clear justification.
- Do not add hidden auto-stash or auto-commit behavior unless explicitly justified and documented.
- Do not scatter rollback ownership across multiple unrelated scripts.
- If broader workflow redesign is required, stop and capture it as a follow-up.

## Output
Return:
1. changed files summary
2. design rationale
3. tests run
4. risks / follow-ups
5. final diff

=== FILE: 04_review_checklist.md ===
# US-AUTO-38: Review Checklist

## Scope Validation
- [ ] Changes stay inside `02_file_scope.md`
- [ ] No backend, frontend, database, or migration changes were introduced
- [ ] No unrelated finalize or registry redesign was introduced
- [ ] No unrelated deployment/runtime work was added

## Functional Validation
- [ ] Success path preserves intended working tree changes
- [ ] Failed execution restores tracked files to the exact pre-run state
- [ ] Failed execution cleans run-owned untracked artifacts
- [ ] Interruption/simulated trap path restores clean state where supported
- [ ] Rollback failure is surfaced explicitly
- [ ] US-AUTO-37 ephemeral path behavior is preserved

## Verification
- [ ] Focused tests cover success path
- [ ] Focused tests cover failure path
- [ ] Focused tests cover pre-mutation failure or safe no-op path
- [ ] Focused tests cover interruption/simulated trap behavior
- [ ] Documentation reflects failed-run rollback semantics

=== FILE: 05_followups.md ===
# US-AUTO-38: Follow-Ups

## Follow-Up Prompt Queue
- Add richer structured rollback diagnostics if current terminal output is insufficient.
- Add preflight classification of failure mode before mutable execution begins.
- Add repeated-failure stop conditions or loop-prevention enforcement if needed.
- Extract shared rollback helper logic only if lifecycle complexity grows enough to justify it.

## Iteration Notes
- Keep this story limited to failed-run automatic rollback.
- Prefer centralized orchestration ownership over distributed cleanup logic.
- Prefer deterministic clean-state restoration over convenience features.
- Do not expand this story into broader workflow redesign.

=== FILE: 06_manual_actions.md ===
# US-AUTO-38: Manual Actions

## Required Human Actions
- Review the bundle pack for scope correctness.
- Materialize and validate the bundle before execution.
- Induce at least one controlled failed run from a clean tree.
- Confirm failed run ends with a clean repository state and no manual cleanup.
- Confirm successful run still preserves intended changes.

## Completion Status
- [ ] No manual actions required
- [ ] Manual actions completed and documented