Story-ID: US-AUTO-46
Version: 1

=== FILE: 00_story.md ===
# US-AUTO-46 — Review operates strictly on committed HEAD

## Story ID and Title
- **Story ID:** `US-AUTO-46`
- **Title:** `Review operates strictly on committed HEAD`

## Objective
Enforce branch fidelity at the review boundary so `review_story_run.sh` and downstream review/classification/gate steps operate only on committed repository state and fail closed when workspace-only changes would make review semantically diverge from `origin/main...HEAD`.

## Scope
- Add a deterministic pre-review guard that blocks review when the primary checkout contains uncommitted changes relevant to repository state.
- Ensure the guard explains the exact remediation path to the operator.
- Add focused regression tests for the committed-HEAD review contract.
- Update workflow documentation so the canonical sequence is explicit at the review boundary as well as the run boundary.
- Materialize the story bundle for US-AUTO-46.

## Non-goals
- Do not redesign the runner pipeline.
- Do not introduce auto-commit behavior.
- Do not relax the clean-tree contract anywhere.
- Do not change merge recommendation semantics.
- Do not redesign AI review prompts or classifier logic beyond what is required for the committed-HEAD contract.
- Do not implement escalation policy changes.
- Do not modify Codex execution internals in `automation/run_codex_task.sh`.

## Dependencies
- `US-AUTO-41` commit-before-run handoff contract.
- `US-AUTO-44` dirty-path operator guidance.
- `US-AUTO-45` deterministic gate reuse.
- Existing review/classification/gate flow and run artifact contract.

## Source of Truth
- `automation/scripts/review_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/run_story.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Current Code Reality
- `run_story.sh` already enforces a clean-tree precondition before execution.
- `US-AUTO-41` established the canonical handoff `materialize -> commit_story_artifacts -> run_story`.
- `US-AUTO-45` made gate reuse deterministic for pinned upstream artifacts.
- A remaining architectural gap exists at the review boundary: review can become semantically unreliable if implementation reality exists only as workspace changes and is not committed to `HEAD`.

## Target Outcome
- Review refuses to proceed when committed `HEAD` is not the sole source of truth for repository state.
- Operator guidance clearly says how to restore fidelity before review.
- Review/classify/gate semantics remain pinned to `origin/main...HEAD`.
- False reject/approve decisions caused by workspace-only divergence are eliminated by fail-closed review entry behavior.

## Atomic Task Isolation Contract
- **Single purpose:** enforce committed-HEAD fidelity at the review boundary.
- **Intent statement:** add a fail-closed review precondition that blocks review when workspace-only changes would make review differ from committed `HEAD`.
- **Out of scope:** escalation redesign, gate logic redesign, runner redesign, auto-commit, bundle-pack sync, broad UX improvements.
- **Allowed file boundary:** only the files listed in `02_file_scope.md`.
- **Forbidden file boundary:** any file not listed as allowed, especially runtime engine internals and unrelated automation stories.
- **Hard-stop condition:** stop immediately if the fix requires changing runner semantics, adding auto-commit behavior, or touching multiple independent findings beyond review-boundary fidelity.
- **Follow-up rule:** newly discovered out-of-scope issues must be captured in `05_followups.md` instead of being folded into this change.
- **Atomic follow-up rule:** each future follow-up prompt must isolate exactly one review finding or one narrowly defined blocker.

## Allowed Files
- `automation/scripts/review_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/run_story.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `tests/test_review_story_run.py`
- `tests/test_analyze_story_run.py`
- `automation/bundle_packs/US-AUTO-46.bundle.md`
- `automation/bundles/active/US-AUTO-46/**`
- `tests/test_review_gate_story_run.py`

## Forbidden Files
- `automation/run_codex_task.sh`
- `automation/scripts/finalize_story.sh`
- `automation/scripts/escalate_story.sh`
- `automation/scripts/commit_story_artifacts.sh`
- `docs/40_ai/**`
- `backend/**`
- `frontend/**`
- `database/**`
- `scripts/migrations/**`

## Risks
- Over-scoping into runner or gate redesign instead of a review-boundary guard.
- Blocking legitimate operator workflows if the dirty-state check is too broad or poorly messaged.
- Reintroducing duplicated clean-tree logic inconsistent with existing preflight contracts.

## Manual Actions
- Materialize the bundle.
- Validate the bundle.
- Review the active prompt for atomic scope before execution.
- After implementation, run the focused review-story test targets and inspect operator messaging in the failure path.

## Acceptance Notes
- Review fails closed when workspace-only changes would undermine committed-HEAD fidelity.
- Operator guidance is deterministic and actionable.
- Tests cover the new blocked path and the clean path.
- Documentation explicitly states that review/classify/gate operate on committed repository state only.

=== FILE: 01_context_bundle.md ===
# US-AUTO-46: Context Bundle

## Source of Truth
- `automation/scripts/review_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/run_story.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Current Code Reality
- The pipeline is now stable through `run -> review -> classify -> gate -> analyze -> finalize`.
- `US-AUTO-41` already forces story artifacts to be committed before `run_story.sh`.
- `US-AUTO-45` makes gate reuse deterministic once pinned review/classification artifacts already exist.
- The unresolved gap is conceptual rather than purely mechanical: review can still be invoked in a checkout whose workspace reality is not identical to committed `HEAD`, which undermines trust in review output.

## Architectural Intent
- Preserve a single repository truth boundary for governance: `origin/main...HEAD`.
- Make review entry fail closed unless that truth boundary is valid at review time.
- Keep the contract explicit, narrow, and operator-readable.
- Prevent downstream governance from evaluating state that was never committed.

## Why This Story Exists
- Escalation, loop detection, and cost-control stories all depend on trustworthy review semantics.
- If review comments on workspace-only state while the contract says review is about committed diff, governance decisions become non-deterministic and misleading.
- This is therefore a P0 architectural invariant even though it can likely be implemented with a small patch.

## Likely Implementation Shape
- Add or strengthen a dirty-worktree guard in `review_story_run.sh` for the primary checkout before review begins.
- Reuse existing operator-guidance patterns where possible rather than inventing a new UX vocabulary.
- Keep downstream scripts aligned with the same boundary contract, but avoid broad refactors unless strictly necessary.
- Add focused tests proving both the blocked case and the happy path.

## Risks
- Duplicating preflight logic inconsistently with `run_story.sh`.
- Checking too many paths and producing false positives from runtime-only artifacts.
- Letting the patch drift into gate redesign or auto-commit territory.

## Acceptance Notes
- The committed-HEAD contract is explicit in both code behavior and docs.
- Review boundary semantics are deterministic.
- The implementation remains atomic and limited to the listed files.

=== FILE: 02_file_scope.md ===
# US-AUTO-46: File Scope

## Files Allowed To Change
- `automation/scripts/review_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/run_story.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `tests/test_review_story_run.py`
- `tests/test_analyze_story_run.py`
- `automation/bundle_packs/US-AUTO-46.bundle.md`
- `automation/bundles/active/US-AUTO-46/**`
- `tests/test_review_gate_story_run.py`

## Files Not Allowed To Change
- `automation/run_codex_task.sh`
- `automation/scripts/finalize_story.sh`
- `automation/scripts/escalate_story.sh`
- `automation/scripts/commit_story_artifacts.sh`
- `docs/40_ai/**`
- `backend/**`
- `frontend/**`
- `database/**`
- `scripts/migrations/**`

## Scope Notes
- Prefer the narrowest possible implementation in `review_story_run.sh`.
- Touch downstream scripts only if needed to keep the review-boundary contract coherent and testable.
- Do not introduce auto-commit or implicit workspace mutation.
- Do not expand into bundle sync or unrelated workflow simplification.

=== FILE: 03_master_prompt.md ===
# US-AUTO-46 PROMPT 1 — Review Boundary Must Use Committed HEAD Only

## Role
You are the Zumbot workflow automation engineer working under the repository's CODEX Operating System.

## Story
US-AUTO-46 — Review operates strictly on committed HEAD.

## Goal
Introduce a fail-closed review-boundary contract so `review_story_run.sh` and downstream governance steps analyze only committed repository state and refuse review when workspace-only changes would make review semantically diverge from `origin/main...HEAD`.

## Source of Truth
- `automation/scripts/review_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/run_story.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Files Allowed To Change
- `automation/scripts/review_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/run_story.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `tests/test_review_story_run.py`
- `tests/test_analyze_story_run.py`
- `automation/bundle_packs/US-AUTO-46.bundle.md`
- `automation/bundles/active/US-AUTO-46/**`
- `tests/test_review_gate_story_run.py`

## Files Not Allowed To Change
- `automation/run_codex_task.sh`
- `automation/scripts/finalize_story.sh`
- `automation/scripts/escalate_story.sh`
- `automation/scripts/commit_story_artifacts.sh`
- `docs/40_ai/**`
- `backend/**`
- `frontend/**`
- `database/**`
- `scripts/migrations/**`

## Implementation Requirements
1. Add the smallest possible committed-HEAD review precondition at review entry.
2. The guard must fail closed when workspace-only changes would make review semantically diverge from committed `HEAD`.
3. The blocked path must explain the exact remediation expectation to the operator.
4. The contract must remain aligned with `origin/main...HEAD` as the review source of truth.
5. Do not add auto-commit behavior.
6. Do not redesign `run_story.sh`.
7. Do not redesign gate logic or escalation policy.
8. Do not modify `automation/run_codex_task.sh`.
9. Add focused regression tests for:
   - blocked review when relevant workspace changes exist;
   - successful review path when checkout is clean;
   - analyze output remains coherent with the new boundary contract if touched.
10. Update documentation so review/classify/gate explicitly operate on committed repository state only.

## Testing
Add or update focused tests that verify:
- review is blocked on relevant uncommitted workspace divergence;
- review succeeds on a clean checkout;
- operator messaging is deterministic and actionable;
- analyze output stays coherent if touched.

## Documentation
Update workflow docs/checklists only where needed to state that review/classify/gate operate on committed repository state only and fail closed when workspace reality diverges from committed `HEAD`.

## Output
Return:
1. changed files summary
2. implementation rationale
3. exact review-boundary guard behavior
4. tests run and results
5. risks or follow-ups discovered but not implemented
6. final diff summary

## Atomic Task Isolation Contract
Atomic Task Isolation is a mandatory execution contract for this run.

You must:
1. Declare the one-sentence task intent before making changes.
2. Keep the patch limited to committed-HEAD review fidelity.
3. Treat any unrelated issue as follow-up work, not inline scope expansion.
4. Stop immediately if the fix requires runner redesign, auto-commit, or multiple independent findings.
5. Record new out-of-scope discoveries as explicit follow-ups instead of folding them into this patch.
6. Treat follow-up prompts as non-exceptional continuations that must also remain atomic.
7. Refuse to proceed if the task becomes non-atomic, underspecified, or split across multiple independent findings.

## Hard Stop Condition
If you discover that this cannot be implemented without changing runner semantics, adding auto-commit, or combining multiple independent review findings, stop and report that the story must be split rather than widening this patch.

=== FILE: 04_review_checklist.md ===
# US-AUTO-46: Review Checklist

## Scope Validation
- [ ] Changes stay inside `02_file_scope.md`
- [ ] No runner redesign was introduced
- [ ] No auto-commit behavior was introduced
- [ ] No escalation-policy changes were bundled into this story
- [ ] No unrelated operator UX cleanup was included

## Functional Validation
- [ ] Review is blocked when the primary checkout has relevant uncommitted changes
- [ ] Review proceeds normally when the checkout is clean
- [ ] Downstream review/classify/gate semantics remain pinned to committed state
- [ ] Operator-facing error text is deterministic and actionable

## Architecture Validation
- [ ] The patch hardens the review boundary instead of redesigning the pipeline
- [ ] The contract remains aligned to `origin/main...HEAD`
- [ ] Existing deterministic gate reuse behavior is not weakened
- [ ] Existing run-time clean-tree contract is not relaxed or contradicted

## Verification
- [ ] Focused tests updated for blocked and clean review paths
- [ ] Docs/checklist/registry updated as needed
- [ ] Manual verification steps recorded
- [ ] Follow-ups captured separately for anything beyond committed-HEAD review fidelity

=== FILE: 05_followups.md ===
# US-AUTO-46: Follow-Ups

## Follow-Up Prompt Queue
- `TBD` — Reuse the same dirty-path classification helper as run preflight if the implementation duplicates logic
- `TBD` — Refine review-boundary false positives if explicitly ephemeral runtime-only artifacts create operator friction

## Iteration Notes
- Keep this story focused on committed-HEAD review fidelity only.
- Do not mix in runner redesign, gate redesign, or auto-commit behavior.
- If implementation discovers a need for helper extraction or broader clean-tree policy refinement, capture it as a separate follow-up rather than widening this story.
- Each future follow-up prompt must remain atomic, independently reviewable, and limited to one finding or blocker.

=== FILE: 06_manual_actions.md ===
# US-AUTO-46: Manual Actions

## Required Human Actions
- Materialize the bundle with `automation/scripts/materialize_story_bundle.sh US-AUTO-46`.
- Validate the active bundle with `automation/scripts/validate_story_bundle.sh automation/bundles/active/US-AUTO-46`.
- Review the materialized prompt and file scope before execution.
- After implementation, run the focused review-story test targets touched by this change.
- Inspect the blocked-path message manually to confirm it tells the operator how to restore committed-HEAD fidelity before review.

## Execution Notes
- Preferred verification path:
  - validate the bundle;
  - run the story on the feature branch;
  - inspect the blocked review path manually;
  - confirm the clean review path still works as expected.
- This story should not be considered complete if the committed-HEAD guard exists only in theory and has not been exercised through at least one realistic blocked-path verification.

## Completion Status
- [ ] No manual actions required
- [ ] Manual actions completed and documented

## Additional Manual Verification
- Confirm review/classify/gate messaging stays aligned with committed repository state semantics.