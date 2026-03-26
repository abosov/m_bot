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
- P1 workflow integrity gap closed by US-AUTO-41: the canonical handoff is now `materialize -> commit_story_artifacts -> run_story`.
- P1 operator preflight gap closed by US-AUTO-44: `run_story.sh` now classifies dirty paths before execution and prints deterministic operator handoff or blocked-state guidance without weakening the clean-tree contract.
- Remaining workflow improvements are downstream optimization stories, not missing clean-tree contract work.

### Optimization Roadmap
- P1 runtime alignment (completed): US-AUTO-32 → US-AUTO-34
- P1 failure safety (completed): US-AUTO-38
- P1 workflow integrity: US-AUTO-41
- P2 anti-cycle enforcement: US-AUTO-25 → US-AUTO-28 (US-AUTO-28 in progress)
- P3 cycle cost reduction: US-AUTO-29 → US-AUTO-31
- P4 operator UX: US-AUTO-18
- Future workflow simplification: make bundle pack the single source of truth and treat bundles/active as materialized-only output

### Next Recommended Story
1. US-AUTO-42 — enforce fail-closed escalation resolution
2. US-AUTO-43 — AI review failure handling and recovery contract
3. US-AUTO-28 — escalation gate for repeated reject stagnation (in progress)
4. US-AUTO-26 — expensive run budget guard
5. US-AUTO-27 — pipeline zone cap
6. US-AUTO-29 — targeted test strategy
7. US-AUTO-30 — review reuse / cache guard
8. US-AUTO-31 — post-run checkpoint workflow
9. US-AUTO-18 — operator UX

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

| US-AUTO-45 | Deterministic review gate artifact reuse | Make review_gate consume pinned review/classification artifacts without recomputation drift | follow-up | Planned | P1 | Draft bundle and contract for pinned-run artifact reuse | US-AUTO-44 | None | Needed because manual classify approved but review_gate recomputed and overwrote the decision for the same run |
| US-AUTO-46 | Reverse bundle sync from active bundle to bundle pack | Add deterministic rebuild flow so packed bundle stays faithful to active bundle files | follow-up | Planned | P1 | Draft bundle and rebuild contract for active-to-pack sync | US-AUTO-44 | None | Needed to eliminate manual pack drift and keep packed bundle source-of-truth aligned with active bundle |

| US-AUTO-18 | Operator UX | Improve console UX | follow-up | Planned | P3 | Keep downstream | US-AUTO-17 | N/A | UX only |

| US-AUTO-25 | Loop detection preflight | Detect repeat execution before run | enforcement | Planned | P1 | Draft bundle | US-AUTO-24 | N/A | Anti-cycle layer |
| US-AUTO-26 | Expensive run budget guard | Cap high-cost reruns | enforcement | Planned | P1 | Draft bundle | US-AUTO-25 | N/A | Cost control |
| US-AUTO-27 | Pipeline zone cap | Limit repeat passes | enforcement | Planned | P1 | Draft bundle | US-AUTO-26 | N/A | Cross-zone control |
| US-AUTO-28 | Escalation gate for repeated reject stagnation | Stop repeated reject governance loops and require explicit human decision | implementation | In Progress | P1 | Fix merge blockers from review (fail-open → RUNS_ROOT → validation → tests) | US-AUTO-27 | automation/bundle_packs/US-AUTO-28.bundle.md | Active implementation; initial version produced valid governance reject revealing fail-open defect and additional hardening needs |
| US-AUTO-42 | Enforce fail-closed escalation resolution | Close fail-open path in run_story.sh for invalid escalation resolution_action | follow-up | Planned | P1 | Draft bundle | US-AUTO-28 | N/A | Atomic governance fix: eliminate fail-open continuation for malformed escalation resolution |
| US-AUTO-29 | Targeted test strategy | Narrow validation scope | follow-up | Planned | P2 | Draft bundle | US-AUTO-28 | N/A | Faster iteration |
| US-AUTO-30 | Review reuse | Cache review safely | follow-up | Planned | P2 | Draft bundle | US-AUTO-29 | N/A | Reduce repetition |
| US-AUTO-31 | Post-run checkpoint | Add checkpoint before rerun | follow-up | Planned | P2 | Draft bundle | US-AUTO-30 | N/A | Stop blind reruns |
| US-AUTO-43 | AI review failure handling | Make pipeline resilient to AI review failures (403/API/network), introduce deterministic failure state, retry contract, and operator guidance | follow-up | Planned | P2 | Draft bundle | US-AUTO-28 | N/A | Handles ai_review step failure (403, timeout, malformed response); ensures ai_review_result.md always exists and analyze provides deterministic recovery path |

---

## Maintenance Rules
- Always register story before execution
- Always update after change
- Prefer conservative status
- Never guess — document uncertainty
