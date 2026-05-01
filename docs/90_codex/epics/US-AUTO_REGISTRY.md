# file: US-AUTO_REGISTRY.md

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

## Source of Truth Model

The US-AUTO workflow enforces strict separation of responsibilities between artifacts:

- **Bundle pack (`automation/bundle_packs/US-AUTO-*.bundle.md`)**
  - The **only authoring source of truth for story definition**
  - All story content, constraints, and contracts must originate here
  - Any changes to story behavior must be made in the bundle pack first

- **Active bundle (`automation/bundles/active/US-AUTO-*`)**
  - A **generated runtime artifact produced by materialize_story_bundle.sh**
  - Must never be edited manually as a source of truth
  - Any drift between bundle pack and active bundle is resolved by re-materialization

- **Registry (`US-AUTO_REGISTRY.md`)**
  - The **epic-level portfolio source of truth**
  - Tracks story existence, status, relationships, and sequencing
  - Must not contain story-level behavioral contracts or duplicate bundle content

Violation of this separation (e.g., editing active bundle directly or duplicating logic in registry) is considered a workflow integrity breach.

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
- US-AUTO-41 — canonical story-artifact handoff before run
- US-AUTO-44 — run preflight dirty-state classification and operator handoff
- US-AUTO-45 — deterministic review gate artifact reuse
- US-AUTO-46 — committed-HEAD review boundary enforcement
- US-AUTO-47 — rerun convergence boundary
- US-AUTO-48 — AI review artifact normalization / hardening
- US-AUTO-49 — runtime scope validation ignores committed active-story bundle artifacts
- US-AUTO-50 — deterministic structured AI review output contract
- US-AUTO-52 — strict manual-finish continuation contract
- US-AUTO-53 — committed-HEAD diff.patch review fidelity
- US-AUTO-54 — rerun-artifact review diff fidelity for US-AUTO-28-F1 path
- US-AUTO-55 — final-HEAD manual-finish review compliance for exact allowed continuation path
- US-AUTO-56 — post-run stage-gate guidance for review eligibility and manual-finish continuation

### Current Gaps
- P0 review-boundary fidelity gap was closed by US-AUTO-46.
- P1 workflow integrity gap was closed by US-AUTO-41.
- P1 operator preflight gap was closed by US-AUTO-44.
- P1 rerun-convergence / manual-finish boundary was closed by US-AUTO-47 and tightened by US-AUTO-52.
- P1 committed-HEAD review evidence fidelity was closed by US-AUTO-53 and US-AUTO-54.
- P1 final-HEAD manual-finish review compliance gap was closed by US-AUTO-55.
- The operator-facing stage guidance gap was closed by US-AUTO-56.
- A new split-story gap was confirmed while attempting US-AUTO-69: companion-artifact execution filtering and rerun-preflight stable-review recomputation are not one atomic change and must be tracked separately.
- A new contract-level follow-up need was confirmed during US-AUTO-73: semantic companion filtering initially remained duplicated across producer and downstream review consumers.
- Attempted centralization in US-AUTO-74 proved non-atomic: centralization alone did not converge because downstream review-fidelity consumption semantics were still implicit.
- US-AUTO-74 is now blocked and narrowed to the already-attempted centralization line.
- The active contract-level continuation is US-AUTO-75, which introduces a producer-owned review-fidelity projection artifact and additive downstream validation while preserving legacy recompute/manual-finish/stale-surface fallback behavior.
- Remaining work after US-AUTO-56 is no longer about missing fail-closed boundary contracts; it is about **cycle-cost reduction, observability, better decision gates, safer reuse, and stronger pre-code discipline**.

### Strategic Directions After US-AUTO-56
1. **Operator guidance and stage-aware workflow clarity**
   - make review eligibility, rerun prohibition, and manual-finish continuation explicit
2. **Cycle-cost reduction**
   - skip useless reruns
   - stop repeated stage loops earlier
   - reduce unnecessary verification scope
3. **Workflow telemetry and continuous improvement**
   - record blockers, reruns, manual interventions, timings, and automation candidates
   - periodically analyze where the process leaks time or scope
4. **Pre-code quality discipline**
   - strengthen fact-only research, design completeness, intent restatement, and phase-scoped delivery before broad implementation runs
5. **Future workflow simplification**
   - move toward bundle-pack-first workflow where active bundle is treated as materialized output, not a second source of truth

### Optimization Roadmap
- P1 runtime alignment (completed): US-AUTO-32 → US-AUTO-34
- P1 failure safety (completed): US-AUTO-38
- P1 workflow integrity (completed): US-AUTO-41
- P1 review-boundary fidelity (completed): US-AUTO-46
- P1 rerun convergence boundary / manual-finish contract (completed): US-AUTO-47
- P1 AI review artifact hardening (completed): US-AUTO-48
- P1 strict manual-finish continuation correction (completed): US-AUTO-52
- P1 committed-HEAD diff.patch review fidelity (completed): US-AUTO-53
- P1 rerun-artifact review diff fidelity (completed): US-AUTO-54
- P1 final-HEAD manual-finish review compliance (completed): US-AUTO-55
- P1 post-run stage-gate guidance (completed): US-AUTO-56
- P1 rerun cost and cycle control after US-AUTO-56:
  - US-AUTO-57 — preflight rerun-skip detection
  - US-AUTO-31 — mandatory analyze gate before rerun or next phase
  - US-AUTO-58 — stage-loop cap and forced escalation threshold
- P1 workflow observability after US-AUTO-56:
  - US-AUTO-61 — workflow telemetry registry
  - US-AUTO-62 — manual workflow event logging and automation-opportunity tagging
  - US-AUTO-63 — periodic workflow analytics and optimization reporting
- P2 safe reuse / refresh / verification optimization:
  - US-AUTO-60 — lightweight review-evidence refresh without full rerun
  - US-AUTO-30 — safe review-artifact reuse eligibility
  - US-AUTO-29 — deterministic story-scoped verification strategy
- P2 pre-code discipline and scope control:
  - US-AUTO-64 — fact-only research artifact for story execution
  - US-AUTO-68 — structured failure packet for follow-up and retry decisions
  - US-AUTO-67 — intent restatement and plan acknowledgement before code edits
  - US-AUTO-65 — explicit design-complete gate before implementation run
  - US-AUTO-66 — phase-scoped implementation runs for multi-step stories
- P3 operator-facing summary UX:
  - US-AUTO-59 — failure-summary and operator decision UX

### Future Optimization (Non-Urgent)
- The pipeline is intentionally fail-closed and preserves strict committed-HEAD and review-artifact fidelity boundaries.
- That strictness is correct, but it still creates operator cost through repeated reruns, late discovery of non-convergence, and manual decision points.
- The next maturity layer is not more fail-open behavior; it is **better early stopping, safer artifact reuse, richer telemetry, and better pre-code scoping**.
- A secondary long-term goal is to turn story execution into a more phase-aware workflow, where research, design, intent acknowledgement, implementation, verification, and follow-up all leave structured evidence.
- Periodic analysis of workflow telemetry should be treated as a first-class input to future follow-up stories.

### Confirmed Workflow Observations
- Repeated rerun after committed-HEAD handoff may fail to converge to a fixed point for some stories, materializing fresh workspace-only changes and making the review pipeline unreachable without manual finish.
- US-AUTO-43 reproduced this non-converging pattern and established the need for a rerun boundary / manual-finish contract.
- First run of `US-AUTO-28-F1` exposed a scope-baseline defect: runtime scope validation included already-committed bundle artifacts for the active story rather than isolating Codex-produced implementation delta.
- US-AUTO-49 corrected that runtime scope-baseline problem.
- US-AUTO-50 resolved the downstream structured-AI-review contract issues and stabilized the review artifact pipeline.
- US-AUTO-54 corrected the rerun-artifact diff fidelity defect for the reproduced US-AUTO-28-F1 path.
- US-AUTO-55 closed the remaining final-HEAD/manual-finish compliance gap for the exact allowed continuation path.
- The earlier US-AUTO-51 line was not merged as-is; it was parked and later superseded by US-AUTO-52, so any surviving PR from that line should be treated as historical and intentionally closed rather than merged.
- After any implementation commit, the ordinary review path must use a fresh committed-head rerun before `ai_review_story_run.sh`, `classify_review_story_run.sh`, or `review_gate_story_run.sh` consume run artifacts.
- Direct `run -> commit -> review` remains invalid for the normal path because it risks stale run evidence.
- The only allowed exception is the explicit manual-finish continuation path after `blocked_non_converging_rerun`; in that mode, do not rerun again until manual finish is complete.
- A transient external `codex exec` failure can still interrupt review-stage automation even when the pinned run and continuation contract are valid; treat such incidents as infrastructure instability, not as workflow-contract defects.
- The current durable `story_change_ledger.jsonl` is useful but too narrow for process analytics; future workflow improvement should add a separate telemetry registry rather than overloading the durable ledger.
- US-AUTO-56 added explicit deterministic stage-gate guidance so operators can see when review-stage is allowed, when commit/discard is required first, and when manual-finish continuation forbids rerun without changing the underlying fail-closed workflow policy.
- Attempted implementation of US-AUTO-69 confirmed a real scope split rather than stale evidence: companion-artifact execution filtering in `automation/run_codex_task.sh` and rerun-preflight / stable-review recomputation in `automation/scripts/run_story.sh` are separate change lines and should not be forced through one continuation story.
- When a story is parked, blocked, or split, the registry must record the explicit return condition: what is already complete, what remains blocked, which follow-up story must land first, and what concrete event makes the parked line eligible to resume.
- A story must always be driven to full completion (run → analyze → review → gate → merge → cleanup) before switching to another story; partial completion or premature context switching is forbidden and considered a workflow violation.
- Review classification may produce false-negative rejects when acceptance conditions are based on coarse heuristics (e.g., code-only vs mixed-scope); such cases must be resolved via explicit decision override and followed by a registry-level contract clarification story.
- US-AUTO-73 implementation confirmed that semantic companion filtering can be delivered, but it also exposed a contract-level maintainability gap: non-runtime companion classification remains duplicated across producer and downstream consumers instead of being centralized in one reusable source of truth.
- Attempted implementation of US-AUTO-74 confirmed that centralizing semantic companion-filter logic is not sufficient by itself: downstream review-fidelity consumers still need an explicit artifact-consumption contract.
- US-AUTO-75 established that projection-based review fidelity must be introduced as an additive layer, not as a rewrite of downstream recompute/manual-finish/stale-surface contracts.
- US-AUTO-75 also exposed a classifier scope-semantics limitation: governance/story artifacts explicitly approved through bundle scope can still be misclassified as out-of-scope delivery files.
- For contract-sensitive downstream stories, bundle instructions must explicitly forbid broad rewrites and preserve existing fallback and producer guard behavior unless a failing test proves a narrower change is impossible.


## Decision Override (Post Review)

- This story operates on mixed scope (code + docs).
- Companion-filter "enabled" mode is only applicable for code-only stories.
- The current story correctly executes with execution_companion_filter_mode=disabled.

- The AI review rejection is based on an inapplicable acceptance condition
  (requirement to demonstrate enabled mode).

- This requirement is NOT valid for mixed-scope stories and is considered
  a false negative in review classification.

Resolution:
- Story is accepted as implemented.
- No additional rerun is required.
- No further changes to implementation are needed.

Follow-up:
- Future stories must explicitly distinguish:
  - code-only stories → must validate enabled mode
  - mixed-scope stories → validate disabled mode correctness only
  

### Story Renaming / Supersession Map
- US-AUTO-51 (`Manual-finish review continuation contract`) → **Superseded by US-AUTO-52** (`Strict manual-finish continuation contract`)
- US-AUTO-26 (`Expensive run budget guard`) → **Superseded by US-AUTO-57** (`Preflight rerun-skip detection`)
- US-AUTO-27 (`Pipeline zone cap`) → **Superseded by US-AUTO-58** (`Stage-loop cap and forced escalation threshold`)
- US-AUTO-18 (`Operator UX`) → **Split / partially absorbed**
  - operator guidance portion is handled by **US-AUTO-56**
  - broader operator-facing summary UX is tracked by **US-AUTO-59**
- US-AUTO-29 remains the same ID but is conceptually re-scoped from “targeted test strategy” to **deterministic story-scoped verification strategy**
- US-AUTO-30 remains the same ID but is re-scoped from “review reuse / cache guard” to **safe review-artifact reuse eligibility**
- US-AUTO-31 remains the same ID but is re-scoped from “post-run checkpoint workflow” to **mandatory analyze gate before rerun or next phase**


### Next Recommended Story
1. US-AUTO-76 — classifier scope semantics for governance story artifacts
2. US-AUTO-31 — mandatory analyze gate before rerun or next phase
3. US-AUTO-58 — stage-loop cap and forced escalation threshold
4. US-AUTO-61 — workflow telemetry registry for run stages, blockers, manual interventions, and timings
5. US-AUTO-62 — manual workflow event logging and automation-opportunity tagging
6. US-AUTO-63 — periodic workflow analytics and optimization reporting
7. US-AUTO-60 — lightweight review-evidence refresh without full rerun
8. US-AUTO-30 — safe review-artifact reuse eligibility
9. US-AUTO-29 — deterministic story-scoped verification strategy
10. US-AUTO-64 — fact-only research artifact for story execution
11. US-AUTO-68 — structured failure packet for follow-up and retry decisions
12. US-AUTO-67 — intent restatement and plan acknowledgement before code edits
13. US-AUTO-65 — explicit design-complete gate before implementation run
14. US-AUTO-66 — phase-scoped implementation runs for multi-step stories
15. US-AUTO-59 — failure-summary and operator decision UX

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
| US-AUTO-38 | Automatic rollback after failed automation run | Restore clean pre-run state after failed execution | implementation | Implemented | P1 | None | US-AUTO-37 | automation/bundles/active/US-AUTO-38/ | Stable merged runtime rollback layer |
| US-AUTO-41 | Story artifacts commit handoff before run | Add explicit commit step between bundle creation and run | follow-up | Implemented | P1 | None | US-AUTO-38 | automation/bundle_packs/US-AUTO-41.bundle.md | Canonical handoff is now `materialize -> commit_story_artifacts -> run_story` |
| US-AUTO-44 | Materialization preflight & operator handoff | Classify dirty state before execution and print deterministic remediation | follow-up | Implemented | P1 | None | US-AUTO-41 | automation/bundle_packs/US-AUTO-44.bundle.md | Story-artifact-only dirtiness hands off to commit flow; unrelated dirtiness blocks |
| US-AUTO-45 | Deterministic review gate artifact reuse | Make review_gate consume pinned review/classification artifacts without recomputation drift | follow-up | Implemented | P1 | None | US-AUTO-44 | automation/bundles/active/US-AUTO-45/ | Stable deterministic gate reuse layer |
| US-AUTO-46 | Review operates strictly on committed HEAD | Enforce branch fidelity so review/classify/gate analyze only committed repository state | enforcement | Implemented | P1 | None | US-AUTO-45 | automation/bundle_packs/US-AUTO-46.bundle.md | Fail-closed boundary for committed `origin/main...HEAD` review semantics |

| US-AUTO-25 | Loop detection preflight | Detect repeat execution before run | enforcement | Planned | P1 | Draft bundle | US-AUTO-24 | N/A | Historical anti-cycle precursor; kept until superseded by later concrete loop-control work |
| US-AUTO-26 | Expensive run budget guard | Historical idea to cap high-cost reruns | enforcement | Superseded | P1 | None | US-AUTO-25 | N/A | Superseded by US-AUTO-57; old framing was too generic and cost-only |
| US-AUTO-27 | Pipeline zone cap | Historical idea to limit repeat passes | enforcement | Superseded | P1 | None | US-AUTO-26 | N/A | Superseded by US-AUTO-58; old “zone” framing no longer matches stage-based workflow model |
| US-AUTO-28 | Escalation gate for repeated reject stagnation | Stop repeated reject governance loops and require explicit human decision | implementation | In Progress | P1 | Resume active implementation after current priority stories | US-AUTO-27 | automation/bundle_packs/US-AUTO-28.bundle.md | Active anti-cycle/escalation line; some downstream blockers were split into follow-ups |
| US-AUTO-42 | Enforce fail-closed escalation resolution | Close fail-open path in run_story.sh for invalid escalation resolution_action | follow-up | Implemented | P1 | None | US-AUTO-28 | automation/bundle_packs/US-AUTO-42.bundle.md | Stable fail-closed escalation resolution validation |
| US-AUTO-43 | AI review failure handling and recovery contract | Enforce fail-closed AI review validation boundary for missing/malformed/incomplete artifacts | follow-up | Implemented | P1 | None | US-AUTO-28 | automation/bundle_packs/US-AUTO-43.bundle.md | Confirmed non-converging rerun pattern as separate workflow observation |
| US-AUTO-47 | Rerun convergence boundary | Bound rerun behavior so reruns stop cleanly at a deterministic convergence boundary | implementation | Implemented | P1 | None | US-AUTO-43 | automation/bundle_packs/US-AUTO-47.bundle.md | Stable convergence/manual-finish boundary layer |
| US-AUTO-48 | AI review artifact contract hardening | Harden AI review artifact normalization and fail-closed evidence emission | follow-up | Implemented | P1 | None | US-AUTO-47 | automation/bundle_packs/US-AUTO-48.bundle.md | Stable normalization / validation layer |
| US-AUTO-28-F1 | Escalation input validation hardening | Enforce strict fail-closed validation of escalation artifact input | follow-up | Implemented | P1 | None | US-AUTO-28 | automation/bundle_packs/US-AUTO-28-F1.bundle.md | Core implementation complete; downstream review-fidelity issues were split out |
| US-AUTO-49 | Scope validation ignores committed active-story bundle artifacts | Exclude committed active-story bundle artifacts from runtime scope validation | follow-up | Implemented | P1 | None | US-AUTO-28-F1 | automation/bundle_packs/US-AUTO-49.bundle.md | Restored scope validation to Codex-produced implementation delta |
| US-AUTO-50 | AI review must produce structured output | Detect prompt echo / malformed AI review output and restore deterministic normalized artifact contract | follow-up | Implemented | P1 | None | US-AUTO-49 | automation/bundle_packs/US-AUTO-50.bundle.md | Remaining rejection accepted as governance outcome, not pipeline defect |
| US-AUTO-51 | Manual-finish review continuation contract | Historical first pass at allowing review continuation after a non-converging rerun and committed manual finish | follow-up | Superseded | P1 | None | US-AUTO-47 | automation/bundle_packs/US-AUTO-51.bundle.md | Parked and superseded by US-AUTO-52; old PR line was intentionally closed rather than merged |
| US-AUTO-52 | Strict manual-finish continuation contract | Narrow stale-HEAD continuation to the exact committed manual-finish case | follow-up | Implemented | P1 | None | US-AUTO-47 | automation/bundles/active/US-AUTO-52/ | Tightened exact-allow / descendant-reject / ancestor-run-history reject semantics |
| US-AUTO-53 | Committed-HEAD diff.patch review fidelity | Make downstream review compare the exact committed implementation diff represented by the pinned run | follow-up | Implemented | P1 | None | US-AUTO-28-F1 | automation/bundle_packs/US-AUTO-53.bundle.md | Stable committed-head diff fidelity |
| US-AUTO-54 | Committed-HEAD review diff fidelity for US-AUTO-28-F1 rerun artifacts | Restore deterministic gate fidelity for the reproduced rerun path | follow-up | Implemented | P1 | None | US-AUTO-28-F1 | automation/bundle_packs/US-AUTO-54.bundle.md | Remaining final-HEAD/manual-finish compliance gap was closed by US-AUTO-55 |
| US-AUTO-55 | Manual-finish final-HEAD review compliance after allowed non-converging rerun continuation | Make exact allowed manual-finish continuation reach downstream review/gate with deterministic final-HEAD compliance | follow-up | Implemented | P1 | None | US-AUTO-54 | automation/bundles/active/US-AUTO-55/ | Final validation succeeded on exact continuation path; transient external Codex 403 treated as infra noise |
| US-AUTO-56 | Post-run stage-gate guidance for review eligibility and manual-finish continuation | Explicitly tell the operator whether review-stage is allowed, whether commit/discard is required, and whether manual-finish continuation forbids rerun | follow-up | Implemented | P1 | None | US-AUTO-55 | automation/bundle_packs/US-AUTO-56.bundle.md | Scope remained limited to deterministic stage-gate messaging and review-eligibility guidance only |
| US-AUTO-57 | Preflight rerun-skip detection | Stop before a full Codex rerun when the next rerun would not change the effective review surface | enforcement | Blocked | P1 | Park implementation; resolved via follow-up US-AUTO-69 | US-AUTO-26 | automation/bundles/active/US-AUTO-57/ | Implementation commit 300d78f, tests passing; BLOCKED by companion-artifact diff (docs/90_codex/epics/US-AUTO_REGISTRY.md) introduced during Codex execution; see US-AUTO-69 |
| US-AUTO-69 | Companion-artifact execution filtering for code-only stories | Isolate the execution-surface filtering half of the blocked US-AUTO-57 follow-up without expanding into rerun-preflight recomputation | split | Split | P1 | Park this split line until US-AUTO-70 lands and proves rerun-preflight / stable-review recomputation separately | US-AUTO-57 | N/A | Split from the attempted continuation: execution filtering belongs to `automation/run_codex_task.sh` + `tests/test_run_codex_task.py`; return condition: resume only after US-AUTO-70 is implemented and the rerun-preflight half is no longer coupled to this line |
| US-AUTO-70 | Rerun-preflight stable-review recomputation for companion-filtered stories | Recompute the effective filtered review surface before rerun/gate so companion-filtered stories do not fail acceptance because rerun-preflight still evaluates the unadjusted surface | follow-up | Implemented | P1 | None | US-AUTO-69 split follow-up | automation/bundle_packs/US-AUTO-70.bundle.md | Scope expanded as required by the accepted bundle-driven implementation: `automation/run_codex_task.sh`, `automation/scripts/run_story.sh`, `automation/scripts/review_story_run.sh`, `automation/scripts/ai_review_story_run.sh`, `automation/scripts/analyze_story_run.sh`, `automation/scripts/classify_review_story_run.sh`, `automation/scripts/review_gate_story_run.sh`, and their focused tests; rerun/manual-finish baseline comparison now recomputes the filtered `changed_files.txt` and `diff.patch` surface from `review_artifact_base` across preflight, analyze, review, classify, and gate decisions, including companion-only HEAD drift after a pinned run, and companion-filtered review bundles/prompts now consume the same filtered changed-files surface instead of the broader companion-inclusive listing; active bundle remains generated output only; completion of this story is still the return condition for resuming the parked US-AUTO-69 line |
| US-AUTO-72 | Explicit companion isolation | Filter execution companion artifacts and enforce non-empty delivery surface | enforcement | Implemented | P1 | None | US-AUTO-69 split | automation/bundles/active/US-AUTO-72/ | Completed and merged |
| US-AUTO-73 | Refine companion-filter semantics for mixed-scope stories | Replace crude "code-only vs mixed-scope" heuristic with path-semantics-based classification of companion artifacts so supporting docs do not invalidate companion-filter validation | governance | Implemented | P1 | None | Follow-up from US-AUTO-70 review conflict | automation/bundles/active/US-AUTO-73/ | Merged in PR #264. Semantic non-runtime companion classification now drives execution and review-surface filtering across run/analyze/review/classify/gate flows. A follow-up centralization/refactoring opportunity remains tracked separately as US-AUTO-74. |
| US-AUTO-74 | Centralize semantic companion-filter contract | Centralize non-runtime companion classification into one shared source of truth for producer and downstream consumers | follow-up | Blocked | P1 | Do not resume until US-AUTO-75 lands and proves additive projection-aware downstream consumption | Follow-up from US-AUTO-73 | N/A | Attempted implementation proved non-atomic: centralization alone did not converge because downstream review-fidelity consumption semantics remained implicit. Return condition: resume only if post-US-AUTO-75 cleanup still requires a narrow centralization-only pass. |
| US-AUTO-75 | Additive review-fidelity projection contract for semantic companion filtering | Introduce producer-owned `semantic_projection.json` and integrate it as a preferred downstream validation fast-path without rewriting recompute/manual-finish/stale-surface fallback contracts | follow-up | In Review | P1 | Merge PR #266 if CI remains green and no maintainer objections | Follow-up from blocked US-AUTO-74 line | automation/bundle_packs/US-AUTO-75.bundle.md | Implementation complete in PR #266. Latest pinned run `automation/runs/US-AUTO-75/2026-05-01_21-39-15` passed `1106 passed`. Automated classifier still rejects governance/story artifacts as out-of-scope despite explicit scope approval; treat as follow-up classifier semantics issue, not a runtime blocker for US-AUTO-75. |
| US-AUTO-76 | Classifier scope semantics for governance story artifacts | Teach review classification/gate semantics that explicitly scope-approved story governance artifacts are allowed delivery context when materialized through the bundle workflow | follow-up | Planned | P1 | Draft bundle after US-AUTO-75 is merged | Follow-up from US-AUTO-75 classifier false reject | N/A | Covers `automation/bundle_packs/<story>.bundle.md`, `automation/bundles/active/<story>/**`, and `docs/90_codex/epics/US-AUTO_REGISTRY.md` when intentionally changed through the approved story workflow. Prevents false MERGE BLOCKER classification for governance artifacts. |
| US-AUTO-29 | Deterministic story-scoped verification strategy | Select the minimal required verification scope for the current story/run instead of always paying full validation cost | follow-up | Planned | P2 | Draft bundle | Re-scoped from original US-AUTO-29 | N/A | Formerly “targeted test strategy”; now broader but still deterministic and story-scoped |
| US-AUTO-30 | Safe review-artifact reuse eligibility | Reuse review-stage artifacts only when the review surface is provably unchanged | follow-up | Planned | P2 | Draft bundle | Re-scoped from original US-AUTO-30 | N/A | Distinct from already-implemented deterministic gate reuse in US-AUTO-45 |
| US-AUTO-31 | Mandatory analyze gate before rerun or next phase | Make `analyze_story_run.sh` an explicit decision gate before rerun, review continuation, or phase advance | follow-up | Planned | P1 | Draft bundle | Re-scoped from original US-AUTO-31 | N/A | Replaces vague checkpoint language with explicit decision-gate semantics |
| US-AUTO-59 | Failure-summary and operator decision UX | Produce compact operator-facing summaries of blockers, allowed next steps, forbidden actions, and cheapest safe path forward | follow-up | Planned | P3 | Draft bundle | US-AUTO-18 | N/A | Remainder of historical operator UX scope after US-AUTO-56 |
| US-AUTO-60 | Lightweight review-evidence refresh without full rerun | Refresh review evidence for committed-HEAD alignment cases without paying for a full Codex execution | follow-up | Planned | P2 | Draft bundle | New post-US-AUTO-56 optimization line | N/A | Separate from safe reuse; focuses on lightweight artifact regeneration |

| US-AUTO-61 | Workflow telemetry registry for run stages, blockers, manual interventions, and timings | Add append-only workflow telemetry separate from the durable story ledger | implementation | Planned | P1 | Draft bundle | New observability line after US-AUTO-56 | N/A | Must not overload the durable `story_change_ledger.jsonl` |
| US-AUTO-62 | Manual workflow event logging and automation-opportunity tagging | Log manual commits, discards, manual-finish usage, and explicit automation candidates | follow-up | Planned | P1 | Draft bundle | US-AUTO-61 | N/A | Captures human intervention points for later optimization |
| US-AUTO-63 | Periodic workflow analytics and optimization reporting | Analyze telemetry periodically to find rerun hotspots, blockers, timing sinks, scope drift, and automation opportunities | follow-up | Planned | P1 | Draft bundle | US-AUTO-61 / US-AUTO-62 | N/A | Intended cadence: lightweight review every few stories; deeper review periodically |

| US-AUTO-64 | Fact-only research artifact for story execution | Produce a structured fact-only research artifact with related files, dependencies, touched layers, and expected verification surface before implementation | follow-up | Planned | P2 | Draft bundle | New pre-code discipline line | N/A | Supports scope control, telemetry, and verification selection |
| US-AUTO-65 | Explicit design-complete gate before implementation run | Require design-complete evidence before implementation run starts | follow-up | Planned | P2 | Draft bundle | US-AUTO-64 | N/A | Prevents broad implementation runs from starting against weak or incomplete design intent |
| US-AUTO-66 | Phase-scoped implementation runs for multi-step stories | Support multi-phase story execution with explicit boundaries and success criteria per phase | implementation | Planned | P2 | Draft bundle | US-AUTO-65 | N/A | Intended for stories that are too wide for one safe atomic implementation run |
| US-AUTO-67 | Intent restatement and plan acknowledgement before code edits | Require explicit restatement of story intent, allowed scope, and immediate plan before edits begin | follow-up | Planned | P2 | Draft bundle | New pre-code control line | N/A | Turns current intent-restatement rule into explicit workflow evidence |
| US-AUTO-68 | Structured failure packet for follow-up and retry decisions | Emit a compact reusable failure packet after blocked/failed stages for follow-up prompts, retry logic, and telemetry | follow-up | Planned | P2 | Draft bundle | US-AUTO-61 / US-AUTO-64 | N/A | Reduces manual context reconstruction after failures |

| US-AUTO-18 | Operator UX | Historical broad operator-experience bucket | follow-up | Split | None | Keep as historical umbrella only | US-AUTO-17 | N/A | Partially absorbed by US-AUTO-56; remainder superseded by US-AUTO-59 |

---

## Maintenance Rules
- Always register story before execution.
- Always update the registry after meaningful change.
- Prefer conservative status.
- Never guess — document uncertainty.
- When a story is parked, blocked, or split, always record the return condition explicitly: the blocking reason, the follow-up story or prerequisite that must complete first, and the concrete event that makes the parked line eligible to resume.
- After any implementation commit, ordinary review must proceed only from a fresh committed-head rerun unless the workflow has explicitly entered manual-finish continuation after `blocked_non_converging_rerun`.
- Never treat `run -> commit -> review` as a valid normal path.
- When manual-finish continuation is active, do not rerun again until manual finish is complete.
- Keep durable story lifecycle evidence (`story_change_ledger.jsonl`) separate from future workflow telemetry / analytics streams.
- When an old story is conceptually replaced rather than merely renamed, keep the old ID in the registry with `Superseded` status and point to the new ID explicitly.
- When a story is re-scoped but remains conceptually continuous, keep the original ID and update the title/summary conservatively.
- After story completion (merge or explicit acceptance decision), the registry MUST be updated immediately to reflect the final status (e.g., Implemented, Superseded, Docs Only) and any decision override or acceptance rationale; leaving stories in outdated status is considered a workflow violation.
