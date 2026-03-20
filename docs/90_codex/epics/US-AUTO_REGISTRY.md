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

### Current Gaps
- Anti-cycle enforcement layer not yet implemented beyond docs/policy guidance
- Cycle-cost reduction work not yet implemented
- Operator UX remains planned and should stay downstream from enforcement work

### Optimization Roadmap
- P1 anti-cycle enforcement: US-AUTO-23 → US-AUTO-27
- P2 cycle cost reduction: US-AUTO-28 → US-AUTO-30
- P3 operator UX: US-AUTO-18

### Next Recommended Story
1. US-AUTO-23 — change ledger
2. US-AUTO-24 — loop detection preflight
3. US-AUTO-25 — expensive run budget guard
4. US-AUTO-26 — pipeline zone cap
5. US-AUTO-27 — escalation gate for loop-risk stories
6. US-AUTO-28 — targeted test strategy
7. US-AUTO-29 — review reuse / cache guard
8. US-AUTO-30 — post-run checkpoint workflow
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
| US-AUTO-22 | Atomic isolation rule | Governance rule | governance | Docs Only | P1 | None | US-AUTO-19 | automation/bundles/active/US-AUTO-22/ | Docs only; policy guidance, not hard enforcement |

| US-AUTO-18 | Operator UX | Improve console UX | follow-up | Planned | P3 | Keep downstream from anti-cycle roadmap | US-AUTO-17 | N/A | Operator-facing UX only; do not absorb enforcement logic |
| US-AUTO-20 | Workflow chaining | Resume + next step logic | follow-up | Implemented | P1 | None | US-AUTO-19 | automation/bundles/active/US-AUTO-20/ | Stage + next-command resume helper shipped |
| US-AUTO-23 | Story change ledger | Record story-level change history | governance | Implemented | P1 | Start US-AUTO-24 bundle | New | automation/bundles/active/US-AUTO-23/ | Evidence-only ledger primitive shipped at `automation/story_change_ledger.jsonl`; records start, review outcome, reject, and finalize outcome |
| US-AUTO-24 | Loop detection preflight | Detect likely repeat execution before run | enforcement | Planned | P1 | Draft bundle | US-AUTO-23 | N/A | Uses ledger signals to stop obvious loop entry before work starts |
| US-AUTO-25 | Expensive run budget guard | Cap repeated high-cost reruns | enforcement | Planned | P1 | Draft bundle | US-AUTO-24 | N/A | Reduces loop cost by blocking repeated expensive run patterns |
| US-AUTO-26 | Pipeline zone cap | Limit repeat passes within pipeline zones | enforcement | Planned | P1 | Draft bundle | US-AUTO-25 | N/A | Prevents cross-zone cycling by capping retries per workflow zone |
| US-AUTO-27 | Escalation gate for loop-risk stories | Require operator escalation on risky loops | enforcement | Planned | P1 | Draft bundle | US-AUTO-26 | N/A | Forces human review when loop-risk signals persist |
| US-AUTO-28 | Targeted test strategy | Narrow validation to impacted scope | follow-up | Planned | P2 | Draft bundle | US-AUTO-27 | N/A | Lowers iteration cost by avoiding unnecessarily broad rerun test scope |
| US-AUTO-29 | Review reuse / cache guard | Reuse prior review context safely | follow-up | Planned | P2 | Draft bundle | US-AUTO-28 | N/A | Cuts repeat review work while guarding against stale-cache loop behavior |
| US-AUTO-30 | Post-run checkpoint workflow | Add checkpoint before another full cycle | follow-up | Planned | P2 | Draft bundle | US-AUTO-29 | N/A | Encourages checkpoint decisions instead of immediate full rerun loops |

---

## Maintenance Rules
- Always register story before execution
- Always update after change
- Prefer conservative status
- Never guess — document uncertainty
