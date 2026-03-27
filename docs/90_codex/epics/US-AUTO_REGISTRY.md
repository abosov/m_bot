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
- P2 anti-cycle enforcement: US-AUTO-25 → US-AUTO-28 (US-AUTO-28 in progress)
- P3 cycle cost reduction: US-AUTO-29 → US-AUTO-31
- P4 operator UX: US-AUTO-18
- Future workflow simplification: make bundle pack the single source of truth and treat bundles/active as materialized-only output

### Confirmed Workflow Observation
- Repeated rerun after committed-HEAD handoff may fail to converge to a fixed point for some stories, materializing fresh workspace-only changes and making the review pipeline unreachable without manual finish. Track this as future operator UX / anti-cycle follow-up work, not as part of US-AUTO-42.
- US-AUTO-43 reproduced this non-converging pattern: after committed-head rerun, fresh workspace-only changes were materialized again, keeping the pinned review pipeline unreachable without manual operator intervention.

### Next Recommended Story
1. US-AUTO-28 — escalation gate for repeated reject stagnation (in progress)
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
| US-AUTO-43 | AI review failure handling and recovery contract | Enforce fail-closed AI review validation boundary so missing, malformed, incomplete, or logically invalid AI review artifacts cannot propagate to classification or gate | follow-up | In Review | P1 | Commit final non-converging implementation tail, open PR with explicit review-boundary blocker note, and spin out follow-up for rerun convergence / operator UX | US-AUTO-28 | automation/bundle_packs/US-AUTO-43.bundle.md | Latest committed-head rerun still materializes fresh workspace-only changes across implementation, tests, and bundle artifacts, preventing pinned ai_review/classify/gate from reaching a fixed point; treat as known convergence blocker rather than continuing blind reruns |
---

## Maintenance Rules
- Always register story before execution
- Always update after change
- Prefer conservative status
- Never guess — document uncertainty
