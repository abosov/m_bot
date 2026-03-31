# US-AUTO Epic Registry

## Purpose
This registry is the durable epic-level source of truth for the US-AUTO automation epic.
It records which `US-AUTO-*` stories exist, how they relate to one another, which story artifact to open next, and the most conservative current status supported by committed repository evidence.

## Scope
Use this registry to track the minimum portfolio-level facts for the epic:
- story ID
- title
- short summary
- story type
- current status
- origin / relationship to other stories
- primary story artifact reference
- notes about uncertainty, splits, cancellation, or supersession

The registry does **not** replace story bundles.

## Status Legend
- Planned
- Bundle Drafted
- Bundle Ready
- In Progress
- Blocked
- In Review
- Implemented
- Docs Only
- Split
- Cancelled
- Superseded

## Type Legend
- implementation
- docs-only
- follow-up
- enforcement
- split
- governance

## Current Epic State

### Stable Layer (working)
- US-AUTO-1 → US-AUTO-7
- US-AUTO-17
- US-AUTO-19
- US-AUTO-20
- US-AUTO-21
- US-AUTO-22 — docs-only governance guidance, not runtime enforcement
- US-AUTO-37 — ephemeral automation paths contract
- US-AUTO-38 — automatic rollback after failed runs

### Current Gaps
- P0 review-boundary fidelity gap closed by US-AUTO-46: review/classify/gate now fail closed when workspace-only changes would diverge from committed `HEAD`.
- P1 workflow integrity gap closed by US-AUTO-41: the canonical handoff is now `materialize -> commit_story_artifacts -> run_story`.
- P1 operator preflight gap closed by US-AUTO-44: `run_story.sh` now classifies dirty paths before execution and prints deterministic operator handoff or blocked-state guidance without weakening the clean-tree contract.
- Remaining workflow improvements are downstream optimization stories, not missing clean-tree contract work.

### Optimization Roadmap
- P1 runtime alignment (completed): US-AUTO-32 → US-AUTO-34
- P1 failure safety (completed): US-AUTO-38
- P1 workflow integrity: US-AUTO-41
- P1 review-boundary fidelity: US-AUTO-46
- P1 rerun convergence boundary / manual finish contract: US-AUTO-47
- P1 manual-finish continuation strictness correction: US-AUTO-52
- P1 committed-HEAD diff.patch review fidelity: US-AUTO-53
- P1 committed-HEAD review diff fidelity for US-AUTO-28-F1 rerun artifacts: US-AUTO-54
- P2 anti-cycle enforcement: US-AUTO-25 → US-AUTO-28 (US-AUTO-28 in progress; US-AUTO-28-F1 implementation is complete, and the remaining blocker is tracked separately as committed-HEAD review artifact fidelity after `review_diff_patch_mismatch` persisted on a clean committed rerun)
- P3 cycle cost reduction: US-AUTO-29 → US-AUTO-31
- P4 operator UX: US-AUTO-18
- Future workflow simplification: make bundle pack the single source of truth and treat bundles/active as materialized-only output


### Future Optimization (Non-Urgent)
- The pipeline is intentionally fail-closed and preserves strict committed-HEAD and review-artifact fidelity boundaries.
- This strictness is correct, but it increases operator cost through extra reruns, longer turnaround time, and higher token usage when the workflow discovers non-convergence late.
- Non-urgent future goal: introduce early rerun-skip detection (preflight convergence check) so the workflow can stop before a full Codex rerun when the next rerun would not change the effective review surface.
- Non-urgent future goal: explore lightweight artifact refresh for committed-HEAD alignment cases where review fidelity can be restored without a full Codex execution.
- Non-urgent future goal: improve operator UX messaging for manual-finish continuation paths so the workflow makes it explicit when rerun is prohibited and manual finish is required.


### Confirmed Workflow Observation
- Repeated rerun after committed-HEAD handoff may fail to converge to a fixed point for some stories, materializing fresh workspace-only changes and making the review pipeline unreachable without manual finish. Track this as future operator UX / anti-cycle follow-up work, not as part of US-AUTO-42.
- US-AUTO-43 reproduced this non-converging pattern: after committed-head rerun, fresh workspace-only changes were materialized again, preventing pinned ai_review/classify/gate from completing; this establishes a confirmed need for a convergence or manual-finish contract in the workflow.
- First run of `US-AUTO-28-F1` confirmed an orchestration blocker: scope validation evaluated a diff that included already-committed bundle artifacts for the active story (`automation/bundle_packs/US-AUTO-28-F1.bundle.md` and `automation/bundles/active/US-AUTO-28-F1/*`). As a result, the run was blocked before the review stage even though Codex produced valid in-scope implementation changes (`automation/scripts/run_story.sh`, `tests/test_run_story.py`). This indicates that the current scope validation uses a branch-level diff instead of isolating Codex-produced changes. Treat this as a separate workflow/scope-baseline follow-up, not as part of `US-AUTO-28-F1`.
- `US-AUTO-49` was implemented and merged to `main`, and its downstream AI review-output blocker was addressed by `US-AUTO-50`. The remaining `US-AUTO-50` review rejection is accepted as a governance/review outcome, not a pipeline integrity defect.
- `US-AUTO-54` corrected the rerun-artifact diff fidelity issue so the review pipeline no longer failed at `review_diff_patch_mismatch` for the reproduced `US-AUTO-28-F1` path. The remaining blocker is a downstream workflow/compliance mismatch: after an allowed manual-finish continuation from `blocked_non_converging_rerun`, AI review and review classification still reject because the pinned run artifacts remain tied to the pre-manual-finish committed HEAD while the final branch tip has advanced. Treat this as a separate final-HEAD/manual-finish review compliance follow-up, not as an implementation defect in `US-AUTO-54`.
- After any implementation commit, the ordinary review path must use a fresh committed-head rerun before `ai_review_story_run.sh`, `classify_review_story_run.sh`, or `review_gate_story_run.sh` consume run artifacts. Direct `run -> commit -> review` is invalid because it risks stale run evidence even when the implementation diff appears unchanged.
- The only allowed exception is the explicit manual-finish continuation path after `blocked_non_converging_rerun`. In that mode, do not rerun again until manual finish is complete; continue only through the exact continuation flow tied to the pinned run evidence.



### Next Recommended Story
1. US-AUTO-55 — manual-finish final-HEAD review compliance after allowed non-converging rerun continuation
2. US-AUTO-26 — expensive run budget guard
3. US-AUTO-27 — pipeline zone cap
4. US-AUTO-29 — targeted test strategy
5. US-AUTO-30 — review reuse / cache guard
6. US-AUTO-31 — post-run checkpoint workflow
7. US-AUTO-18 — operator UX

---

## Registry Table

| US ID | Title | Summary | Type | Status | Priority | Next Action | Origin | Story Artifact | Notes |
|------|------|--------|------|--------|----------|------------|--------|----------------|------|
| US-AUTO-1 | Story bundle bootstrap automation | Bundle system bootstrap | implementation | Implemented | P0 | None | Initial | automation/bundles/active/US-AUTO-1/ | Stable |
| US-AUTO-2 | Run story launcher | STORY_ID execution | implementation | Implemented | P0 | None | US-AUTO-1 | automation/bundles/active/US-AUTO-2/ | Stable |
| US-AUTO-3 | Review launcher | Review flow | implementation | Implemented | P0 | None | US-AUTO-2 | automation/bundles/active/US-AUTO-3/ | Stable |
| US-AUTO-4 | Lean context | Reduced context | implementation | Implemented | P0 | None | Optimization | automation/bundles/active/US-AUTO-4/ | Stable |
| US-AUTO-5 | AI review | Auto review | implementation | Implemented | P0 | None | US-AUTO-3 | automation/bundles/active/US-AUTO-5/ | Stable |
| US-AUTO-6 | Review classification | Classification | implementation | Implemented | P0 | None | US-AUTO-5 | automation/bundles/active/US-AUTO-6/ | Stable |
| US-AUTO-7 | Stable evidence | Commit-range evidence | implementation | Implemented | P0 | None | US-AUTO-6 | automation/bundles/active/US-AUTO-7/ | Stable |

| US-AUTO-17 | Repository map v2 | Context injection | implementation | Implemented | P1 | None | Follow-up | automation/bundles/active/US-AUTO-17/ | Stable |
| US-AUTO-19 | Failure surfacing | Run diagnostics | implementation | Implemented | P1 | None | US-AUTO-17 | automation/bundles/active/US-AUTO-19/ | Stable |

| US-AUTO-21 | Clean commit boundary | Enforce clean state | enforcement | Implemented | P1 | None | US-AUTO-19 | automation/bundles/active/US-AUTO-21/ | Stable |
| US-AUTO-22 | Atomic isolation rule | Governance rule | governance | Docs Only | P1 | None | US-AUTO-19 | automation/bundles/active/US-AUTO-22/ | Docs only |

| US-AUTO-37 | Ephemeral automation paths contract | Remove false dirty-tree from workflow-owned artifacts | enforcement | Implemented | P1 | None | US-AUTO-24 | automation/bundles/active/US-AUTO-37/ | Stabilized ledger + ephemeral paths |
| US-AUTO-38 | Automatic rollback after failed automation run | Restore clean pre-run state after failed execution | implementation | Implemented | P1 | Start US-AUTO-41 bundle | US-AUTO-37 | automation/bundles/active/US-AUTO-38/ | Merged in PR #217; added automatic rollback for failed or interrupted runs and updated rollback contract docs/tests |

| US-AUTO-41 | Story artifacts commit handoff before run | Add explicit commit step between bundle creation and run | follow-up | Implemented | P1 | None | US-AUTO-38 | automation/bundle_packs/US-AUTO-41.bundle.md | Added `commit_story_artifacts.sh`, restricted staging to canonical story-artifact roots, kept unrelated dirty paths fail-closed except the exact ephemeral ledger path, and made `run_story.sh` print deterministic remediation |

| US-AUTO-44 | Materialization preflight & operator handoff | Make run preflight explicitly classify dirty state and print deterministic operator remediation before execution | follow-up | Implemented | P1 | None | US-AUTO-41 | automation/bundle_packs/US-AUTO-44.bundle.md | Added first-class preflight in `run_story.sh` with explicit classify/pass markers; story-artifact-only dirtiness now hands off to review changes -> `commit_story_artifacts.sh` -> rerun, while unrelated dirty paths block outside the handoff flow |

| US-AUTO-45 | Deterministic review gate artifact reuse | Make review_gate consume pinned review/classification artifacts without recomputation drift | follow-up | Implemented | P1 | None | US-AUTO-44 | automation/bundles/active/US-AUTO-45/ | Merged in PR #224; gate now deterministically reuses pinned review/classification artifacts without upstream recomputation drift |
| US-AUTO-46 | Review operates strictly on committed HEAD | Enforce branch fidelity so review/classify/gate analyze only committed repository state and never drift from workspace-only changes | enforcement | Implemented | P1 | None | US-AUTO-45 | automation/bundle_packs/US-AUTO-46.bundle.md | Added fail-closed review boundary guard across review, AI review, classification, gate, and analyze messaging so workspace-only divergence cannot change committed `origin/main...HEAD` review semantics; analyze now honors the same ledger-only exemption as the runtime review boundary |

| US-AUTO-18 | Operator UX | Improve console UX | follow-up | Planned | P3 | Keep downstream | US-AUTO-17 | N/A | UX only |

| US-AUTO-25 | Loop detection preflight | Detect repeat execution before run | enforcement | Planned | P1 | Draft bundle | US-AUTO-24 | N/A | Anti-cycle layer |
| US-AUTO-26 | Expensive run budget guard | Cap high-cost reruns | enforcement | Planned | P1 | Draft bundle | US-AUTO-25 | N/A | Cost control |
| US-AUTO-27 | Pipeline zone cap | Limit repeat passes | enforcement | Planned | P1 | Draft bundle | US-AUTO-26 | N/A | Cross-zone control |
| US-AUTO-28 | Escalation gate for repeated reject stagnation | Stop repeated reject governance loops and require explicit human decision | implementation | In Progress | P1 | Fix merge blockers from review (fail-open → RUNS_ROOT → validation → tests) | US-AUTO-27 | automation/bundle_packs/US-AUTO-28.bundle.md | Active implementation; initial version produced valid governance reject revealing fail-open defect and additional hardening needs |
| US-AUTO-42 | Enforce fail-closed escalation resolution | Close fail-open path in run_story.sh for invalid escalation resolution_action | follow-up | Implemented | P1 | None | US-AUTO-28 | automation/bundle_packs/US-AUTO-42.bundle.md | Merged in PR #230; run_story.sh now fails closed for missing, blank, malformed, and unknown escalation resolution_action values with deterministic operator guidance and focused regression coverage |
| US-AUTO-29 | Targeted test strategy | Narrow validation scope | follow-up | Planned | P2 | Draft bundle | US-AUTO-28 | N/A | Faster iteration |
| US-AUTO-30 | Review reuse | Cache review safely | follow-up | Planned | P2 | Draft bundle | US-AUTO-29 | N/A | Reduce repetition |
| US-AUTO-31 | Post-run checkpoint | Add checkpoint before rerun | follow-up | Planned | P2 | Draft bundle | US-AUTO-30 | N/A | Stop blind reruns |
| US-AUTO-43 | AI review failure handling and recovery contract | Enforce fail-closed AI review validation boundary so missing, malformed, incomplete, or logically invalid AI review artifacts cannot propagate to classification or gate | follow-up | Implemented | P1 | None | US-AUTO-28 | automation/bundle_packs/US-AUTO-43.bundle.md | Merged in PR #232; implementation and tests are complete, but committed-head reruns do not converge to a fixed point and can re-materialize workspace-only changes, preventing pinned review chain completion without manual intervention; tracked as separate convergence/operator UX follow-up |
| US-AUTO-47 | Rerun convergence boundary | Bound rerun behavior so reruns stop cleanly at a deterministic convergence boundary instead of widening in place. | implementation | Implemented | P1 | Merged in PR #236; no further action in this story. | US-AUTO-43 | automation/bundle_packs/US-AUTO-47.bundle.md | Merged to `main`. During review/run validation, a separate AI review artifact contract issue was observed and split out into follow-up US-AUTO-48. |
| US-AUTO-48 | AI review artifact contract hardening | Harden the AI review artifact contract so malformed or incomplete AI review output cannot leave the pipeline without a valid normalized `ai_review_result.md` or explicit fail-closed evidence for downstream stages. | follow-up | Implemented | P1 | None | US-AUTO-47 | automation/bundle_packs/US-AUTO-48.bundle.md | Merged in PR #239. AI review now normalizes `ai_review_result.md` from preserved raw output when possible and otherwise emits deterministic `ai_review_normalization_failed` evidence so analyze, classify, and gate fail closed consistently. |
| US-AUTO-28-F1 | Escalation input validation hardening | Enforce strict fail-closed validation of escalation artifact input (schema, origin, transitions) | follow-up | Implemented | P1 | None | US-AUTO-28 | automation/bundle_packs/US-AUTO-28-F1.bundle.md | Implementation was resumed on a clean branch from current `main`, the escalation compatibility regression was fixed, and strict fail-closed escalation artifact identity validation was completed in `automation/scripts/run_story.sh` with focused regression coverage in `tests/test_run_story.py`. Fresh committed-head `run_story.sh` and `analyze_story_run.sh` succeeded with matching HEAD consistency. The remaining `review_diff_patch_mismatch` rejection is treated as an external committed-HEAD review artifact fidelity blocker, not an implementation defect in this story. |
| US-AUTO-49 | Scope validation ignores committed active-story bundle artifacts | Exclude already-committed canonical bundle artifacts for the active story from runtime scope validation so only Codex-produced implementation delta is checked | follow-up | Implemented | P1 | None | US-AUTO-28-F1 | automation/bundle_packs/US-AUTO-49.bundle.md | Merged in PR #243; implemented runtime scope-baseline fix in `automation/run_codex_task.sh` with regression coverage in `tests/test_run_codex_task.py`. During review, a separate AI review-output blocker was confirmed and split into US-AUTO-50 |
| US-AUTO-50 | AI review must produce structured output | Detect and fail closed on prompt-echo / malformed AI review output, and restore a deterministic normalized AI review artifact contract for classify/gate | follow-up | Implemented | P1 | None | US-AUTO-49 | automation/bundle_packs/US-AUTO-50.bundle.md | Merged in PR #245. Pipeline fidelity issues were resolved: changed_files generation mismatch fixed, diff.patch mismatch fixed via story-artifact filtering in run_codex_task.sh, and gate now reaches review_classification without internal inconsistencies. Final state accepted as-is: pipeline is stable and reproducible, and the remaining reject comes from review_classification/governance concerns rather than a system error. Reviewer remarks about bundle-artifact governance and prefix matcher risk were not pursued further in this story. |
| US-AUTO-52 | Strict manual-finish continuation contract | Narrow stale-HEAD continuation to the exact committed manual-finish case tied to immediate prior non-converging rerun evidence, and fail closed for ancestor-run or descendant-commit variants | follow-up | Implemented | P1 | None | US-AUTO-47 | automation/bundles/active/US-AUTO-52/ | Corrective follow-up that tightened review gate continuation predicate and added explicit regression coverage for exact-allow, descendant-reject, and ancestor-run-history reject behavior without widening orchestration scope. |
| US-AUTO-53 | Committed-HEAD diff.patch review fidelity | Make downstream review compare the exact committed implementation diff represented by the pinned run so `review_diff_patch_mismatch` rejects only true stale or inconsistent evidence | follow-up | Implemented | P1 | None | US-AUTO-28-F1 | automation/bundle_packs/US-AUTO-53.bundle.md | Implemented by making `run_codex_task.sh` generate `diff.patch` through a temporary intent-to-add index so mixed tracked and newly materialized files are emitted in the same canonical order as committed `git diff`, with focused regression coverage for committed-match acceptance and true mismatch rejection in `tests/test_run_codex_task.py` and `tests/test_review_gate_story_run.py`. |
| US-AUTO-54 | Committed-HEAD review diff fidelity for US-AUTO-28-F1 rerun artifacts | Determine why `review_gate_story_run.sh` still reports `review_diff_patch_mismatch` for `US-AUTO-28-F1` after a clean committed-head rerun with matching manifest HEAD, and restore deterministic gate fidelity for that exact rerun path | follow-up | In Progress | P1 | Verify the gate-side normalization fix for pinned same-story bundle sections in `diff.patch`, then prepare the narrow patch for commit | US-AUTO-28-F1 | automation/bundle_packs/US-AUTO-54.bundle.md | Narrow follow-up created after `US-AUTO-28-F1` implementation completed on committed HEAD but review gate still rejected with `review_diff_patch_mismatch` on rerun artifacts despite clean tree and matching manifest HEAD. Scope is limited to rerun-artifact fidelity at the review boundary. |
| US-AUTO-55 | Manual-finish final-HEAD review compliance after allowed non-converging rerun continuation | Make downstream AI review, classification, and gate treat an allowed manual-finish continuation consistently with final reviewed HEAD semantics, or produce compliant final-HEAD evidence without reopening the rerun loop | follow-up | Planned | P1 | Draft bundle | US-AUTO-54 | N/A | Narrow follow-up created after `US-AUTO-54` fixed rerun diff fidelity but final merge still rejected because the allowed manual-finish path advanced HEAD beyond the pinned rerun manifest, causing downstream workflow/branch compliance failure. Scope is limited to final-HEAD review compliance for approved manual-finish continuation. |

---

## Maintenance Rules
- Always register story before execution
- Always update after change
- Prefer conservative status
- Never guess — document uncertainty
- After any implementation commit, ordinary review must proceed only from a fresh committed-head rerun unless the workflow has explicitly entered manual-finish continuation after `blocked_non_converging_rerun`.
- Never treat `run -> commit -> review` as a valid normal path.
- When manual-finish continuation is active, do not rerun again until manual finish is complete.
