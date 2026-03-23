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
- Story execution workflow has a missing handoff between bundle materialization and clean-tree enforcement before `run_story.sh`.
- Story artifacts (`bundle.md` and `bundles/active`) are expected to be created uncommitted, but no canonical commit step exists.
- This creates repeated operator friction and risks pressure to weaken clean-tree contract.
- Operator workflow still lacks a deterministic bridge between authoring and execution phases.

### Optimization Roadmap
- P1 runtime alignment (completed): US-AUTO-32 → US-AUTO-34
- P1 failure safety (completed): US-AUTO-38
- P1 workflow integrity: US-AUTO-41
- P2 anti-cycle enforcement: US-AUTO-25 → US-AUTO-28
- P3 cycle cost reduction: US-AUTO-29 → US-AUTO-31
- P4 operator UX: US-AUTO-18

### Next Recommended Story
1. US-AUTO-25 — loop detection preflight
2. US-AUTO-26 — expensive run budget guard
3. US-AUTO-27 — pipeline zone cap
4. US-AUTO-28 — escalation gate for loop-risk stories
5. US-AUTO-29 — targeted test strategy
6. US-AUTO-30 — review reuse / cache guard
7. US-AUTO-31 — post-run checkpoint workflow
8. US-AUTO-18 — operator UX

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

| US-AUTO-41 | Story artifacts commit handoff before run | Add explicit commit step between bundle creation and run | follow-up | In Progress | P1 | Implement commit-before-run contract | US-AUTO-38 | automation/bundle_packs/US-AUTO-41.bundle.md | Split delivery: runtime stabilization landed earlier; current work completes the missing commit-before-run contract |

| US-AUTO-18 | Operator UX | Improve console UX | follow-up | Planned | P3 | Keep downstream | US-AUTO-17 | N/A | UX only |

| US-AUTO-25 | Loop detection preflight | Detect repeat execution before run | enforcement | Planned | P1 | Draft bundle | US-AUTO-24 | N/A | Anti-cycle layer |
| US-AUTO-26 | Expensive run budget guard | Cap high-cost reruns | enforcement | Planned | P1 | Draft bundle | US-AUTO-25 | N/A | Cost control |
| US-AUTO-27 | Pipeline zone cap | Limit repeat passes | enforcement | Planned | P1 | Draft bundle | US-AUTO-26 | N/A | Cross-zone control |
| US-AUTO-28 | Escalation gate | Require operator intervention on loops | enforcement | Planned | P1 | Draft bundle | US-AUTO-27 | N/A | Human override |
| US-AUTO-29 | Targeted test strategy | Narrow validation scope | follow-up | Planned | P2 | Draft bundle | US-AUTO-28 | N/A | Faster iteration |
| US-AUTO-30 | Review reuse | Cache review safely | follow-up | Planned | P2 | Draft bundle | US-AUTO-29 | N/A | Reduce repetition |
| US-AUTO-31 | Post-run checkpoint | Add checkpoint before rerun | follow-up | Planned | P2 | Draft bundle | US-AUTO-30 | N/A | Stop blind reruns |

---

## Maintenance Rules
- Always register story before execution
- Always update after change
- Prefer conservative status
- Never guess — document uncertainty