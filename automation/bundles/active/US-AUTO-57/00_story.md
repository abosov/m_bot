## Story ID and Title
US-AUTO-57 — Preflight rerun-skip detection

## Objective
Add a fail-closed preflight decision in `automation/scripts/run_story.sh` that stops a new Codex rerun when the pipeline can conservatively prove that rerunning would not change the effective review surface for the current committed state. This story reduces cycle cost and avoids avoidable manual-finish situations without relaxing committed-HEAD or review-boundary invariants. :contentReference[oaicite:0]{index=0}

## Scope
- Add deterministic preflight logic in `automation/scripts/run_story.sh` for the current story ID.
- Inspect prior committed-head run evidence for the same story and compare it against the current committed repository state before invoking Codex.
- Detect the narrow case where a new rerun would not change the effective review surface for the next review-stage decision.
- Emit explicit fail-closed operator guidance that tells the operator to stop rerunning and use the existing safe next step instead.
- Preserve ordinary rerun behavior when the preflight cannot prove sameness safely.

## Non-goals
- Do not change `analyze_story_run.sh` decision semantics.
- Do not add mandatory analyze enforcement; that remains in US-AUTO-31. :contentReference[oaicite:1]{index=1}
- Do not add stage-loop counters or escalation thresholds; that remains in US-AUTO-58. :contentReference[oaicite:2]{index=2}
- Do not introduce review-artifact reuse; that remains in US-AUTO-30 and US-AUTO-60. :contentReference[oaicite:3]{index=3}
- Do not add workflow telemetry or analytics; that remains in US-AUTO-61, US-AUTO-62, and US-AUTO-63. :contentReference[oaicite:4]{index=4}
- Do not relax committed-HEAD, manual-finish, or review-boundary contracts.

## Dependencies
- US-AUTO-41 — canonical story-artifact handoff before run
- US-AUTO-44 — run preflight dirty-state classification and operator handoff
- US-AUTO-46 — committed-HEAD review boundary enforcement
- US-AUTO-47 — rerun convergence boundary
- US-AUTO-52 — strict manual-finish continuation contract
- US-AUTO-56 — post-run stage-gate guidance for review eligibility and manual-finish continuation :contentReference[oaicite:5]{index=5} :contentReference[oaicite:6]{index=6}

## Source of Truth
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/scripts/run_story.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- Existing run artifacts under `automation/runs/<STORY_ID>/...`

## Current Code Reality
- After US-AUTO-56, the pipeline gives stage-gate guidance after a run has completed, but `run_story.sh` still proceeds into a full Codex rerun whenever the normal preflight dirtiness checks pass.
- The current pipeline can detect non-converging rerun behavior only after paying the cost of another run and then analyzing the resulting artifacts.
- Repeated reruns with no effective review-surface change still consume time and cost, and may lead the operator into late-discovered manual-finish handling.
- The registry explicitly positions post-US-AUTO-56 work around cycle-cost reduction, early stopping, better decision gates, safer reuse, and observability. :contentReference[oaicite:7]{index=7}

## Target Outcome
- `run_story.sh` performs an additional fail-closed preflight check before Codex execution.
- When the script can prove that a new rerun would not change the effective review surface, it stops immediately with deterministic guidance instead of starting Codex.
- The emitted guidance is explicit enough for the operator to choose the cheapest safe next step.
- If the script cannot prove sameness safely, it allows the run to continue rather than guessing.
- The implementation keeps blast radius narrow and preserves downstream contracts unchanged.

## Atomic Task Isolation Contract
- This story is limited to preflight rerun-skip detection only.
- The implementation must not change review-stage contracts, manual-finish rules, escalation behavior, telemetry shape, registry schema, or bundle validation rules.
- Allowed behavior change: block a new rerun earlier when no meaningful review-surface change can occur.
- Disallowed behavior change: modifying downstream stage semantics or adding alternative fallback execution paths.
- The implementation must stay deterministic and fail-closed when evidence is missing, ambiguous, stale, or inconsistent.

## Risks
- Complexity: Medium
- Risk: Medium
- Blast Radius: Narrow
- Primary regression risk: incorrectly skipping a rerun that should have been allowed.
- Primary scope-drift risk: accidentally expanding into analyze enforcement, stage-loop control, or review-artifact reuse.
- Control for risk: only skip when sameness is provable from committed-head evidence and existing run artifacts; otherwise continue ordinary run behavior.
- Recovery expectation: operator can still run the normal path if skip is not provable; no destructive state should be introduced by the preflight.
- Observability expectation: the skip path must print a deterministic reason and a deterministic next-step message.

## Manual Actions
- Update the registry entry for `US-AUTO-57` from `Planned` to `Bundle Drafted` after materialize and validate succeed.
- Keep `US-AUTO-56` as implemented; no additional status change is needed there.
- Preserve follow-up sequencing for `US-AUTO-31` and `US-AUTO-58` as separate stories.
- Use the standard workflow: bundle pack → materialize → validate → registry update → branch creation → commit bundle artifacts → run story → analyze story run. :contentReference[oaicite:8]{index=8}

## Acceptance Notes
- Intent: stop paying for a rerun when the pipeline can already prove that the next rerun would not change the effective review surface.
- Responsibility boundary: this story owns only the preflight decision before Codex execution and the associated operator guidance.
- Fail-closed contract: ambiguous, missing, or stale evidence must never cause a skip; in those cases the script must continue with ordinary run behavior.
- Pipeline invariants preserved:
  - no automation on `main`
  - no fail-open review boundary
  - no bypass of committed-HEAD semantics
  - no rerun during active manual-finish continuation unless the existing contract already allows it
- No decomposition is required; the story is atomic because it addresses one narrow problem with one stage boundary.
- A deterministic review outcome is preserved because the story either blocks before run with explicit guidance or leaves the existing pipeline unchanged.

