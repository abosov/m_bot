# Story Bundle Pack
Story-ID: US-AUTO-57
Version: 1

=== FILE: 00_story.md ===
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
- Keep implementation strictly inside the allowed runtime scope for this story.
- Preserve follow-up sequencing for `US-AUTO-31` and `US-AUTO-58` as separate stories.
- Use the standard workflow for implementation artifacts only: bundle pack → materialize → validate → branch creation → commit bundle artifacts → run story → analyze story run.
- Treat any attempted registry edit during `run_story.sh` as scope drift and reject it. :contentReference[oaicite:8]{index=8}

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

=== FILE: 01_context_bundle.md ===
## Source of Truth
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/scripts/run_story.sh`
- `automation/scripts/analyze_story_run.sh`
- Existing committed-head run artifacts under `automation/runs/<STORY_ID>/...`
- The implemented workflow contracts from US-AUTO-41, US-AUTO-44, US-AUTO-46, US-AUTO-47, US-AUTO-52, and US-AUTO-56

## Current Code Reality
- The current preflight in `run_story.sh` focuses on dirty-state classification, story-artifact handoff, and branch-safety checks.
- Review-stage eligibility and manual-finish guidance are surfaced after runs and analysis, not before Codex execution.
- Repeated reruns can still happen even when the effective review surface for the current committed HEAD would remain unchanged.
- The registry identifies post-US-AUTO-56 remaining work as cycle-cost reduction, early stopping, better decision gates, safer reuse, and observability. :contentReference[oaicite:9]{index=9}

## Architectural Intent
- Add an early fail-closed stop only where sameness is provable.
- Reuse existing committed-head evidence concepts rather than inventing a second workflow truth.
- Reduce wasted execution cost without weakening review integrity or manual-finish correctness.
- Keep the change narrow: preflight detection only, no orchestration redesign.
- Preserve separation of concerns:
  - US-AUTO-57 handles early rerun skip detection
  - US-AUTO-31 handles mandatory analyze gating
  - US-AUTO-58 handles repeated stage-loop escalation
  - US-AUTO-30 and US-AUTO-60 handle safe reuse and lightweight refresh later :contentReference[oaicite:10]{index=10}

## Risks
- If sameness detection is too weak, the story provides little value.
- If sameness detection is too aggressive, the script may block a useful rerun.
- If the implementation reads stale or invalid run evidence, the skip decision could become unsafe.
- If the code drifts into analyze enforcement or review reuse, scope will no longer be atomic.
- The story must therefore use a conservative proof rule and fall back to ordinary run behavior whenever proof is incomplete.

## Acceptance Notes
- The safest interpretation of “would not change the effective review surface” is the narrow one: skip only when existing committed-head evidence already demonstrates sameness for the current committed state.
- The skip path must be explicit and observable in console output.
- The ordinary path must remain available when proof does not exist.
- Registry logic after bundle preparation:
  - `US-AUTO-57` should be treated as `Bundle Drafted`
  - `US-AUTO-56` remains `Implemented`
  - no new follow-up story is required to keep this story atomic

=== FILE: 02_file_scope.md ===
## Files Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/scripts/_helpers.sh`
- `tests/test_run_story.py`

## Files Not Allowed To Change
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/run_codex_task.sh`
- `automation/story_change_ledger.jsonl`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/*`
- `automation/bundles/active/*`
- Any unrelated tests outside `tests/test_run_story.py`

## Scope Notes
- Allowed change types:
  - add preflight helper logic for rerun-skip detection
  - read existing run evidence conservatively
  - emit deterministic operator guidance
  - add or adjust focused tests only for the new preflight behavior in `tests/test_run_story.py`
- Forbidden change types:
  - changing analyze semantics
  - changing review-stage script inputs or outputs
  - changing manual-finish continuation rules
  - adding telemetry persistence
  - changing registry structure
  - changing bundle materialization or validation contracts
- Anti-scope-drift rule:
  - do not implement analyze enforcement, stage-loop escalation, artifact reuse, or lightweight artifact refresh in this story
- Fail-closed rule:
  - on uncertainty, missing evidence, stale evidence, parse failure, or ambiguous comparison, do not skip the rerun

=== FILE: 03_master_prompt.md ===
## Role
You are the implementation engineer for US-AUTO-57 working inside the Codex automation pipeline with strict fail-closed workflow rules.

## Goal
Implement a narrow preflight rerun-skip detector in `automation/scripts/run_story.sh` that blocks a new Codex rerun only when the pipeline can conservatively prove that rerunning would not change the effective review surface for the current committed state.

## Source of Truth
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/scripts/run_story.sh`
- Existing run evidence format already consumed by the pipeline
- Existing workflow invariants from US-AUTO-41, US-AUTO-44, US-AUTO-46, US-AUTO-47, US-AUTO-52, and US-AUTO-56

## Files Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/scripts/_helpers.sh`
- `tests/test_run_story.py`

## Files Not Allowed To Change
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/run_codex_task.sh`
- `automation/story_change_ledger.jsonl`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/*`
- `automation/bundles/active/*`
- Any unrelated tests outside `tests/test_run_story.py`

## Atomic Task Isolation Contract
- Solve one problem only: prevent a wasted rerun before Codex execution when sameness is provable.
- Do not implement mandatory analyze gating.
- Do not implement stage-loop counters or escalation.
- Do not implement review-artifact reuse or lightweight review refresh.
- Do not relax committed-HEAD, manual-finish, or review-boundary contracts.
- Hard stop: if the change requires broad orchestration redesign, stop and keep the implementation within the allowed files and narrow preflight boundary.

## Execution Gate
- The new logic must run before Codex execution starts.
- The new logic must preserve all existing preflight gates.
- The new logic must be fail-closed:
  - if evidence is missing, ambiguous, stale, malformed, or inconsistent, do not skip
  - if proof of sameness exists, stop the rerun and emit deterministic guidance
- The skip decision must not mutate existing run artifacts and must not fabricate new review evidence.

## Implementation Requirements
- Use existing committed-head and run-evidence concepts already present in the pipeline rather than inventing a new external state source.
- Detect the narrow safe case where the current story already has prior run evidence for the same effective committed review surface and a new rerun would not change that surface.
- Emit a deterministic reason string and guidance message that clearly explains that the rerun is being blocked because it would not change the effective review surface.
- Keep the implementation conservative:
  - sameness must be proven, not assumed
  - uncertainty must fall through to the ordinary run path
- Preserve the current successful paths when skip is not provable.
- Preserve branch-safety, dirty-state classification, and story-artifact handoff behavior already implemented in the pipeline.
- Keep helper extraction small and local if needed; avoid broad utility redesign.
- Keep console messaging aligned with the operator-guidance style introduced by US-AUTO-56.
- Do not modify `docs/90_codex/epics/US-AUTO_REGISTRY.md`; registry maintenance is outside implementation scope for this story and any attempted registry edit must be treated as forbidden scope drift.

## Verification Requirements
- Add focused automated coverage in `tests/test_run_story.py` for:
  - rerun blocked when safe sameness proof exists
  - rerun proceeds when no prior proof exists
  - rerun proceeds when evidence is stale, malformed, or ambiguous
  - skip path does not invoke Codex execution
  - skip path emits deterministic guidance
- Do not modify unrelated tests to force green behavior.
- Preserve external contracts; fix internal logic rather than weakening expectations.

## Output
- A narrow implementation in the allowed files only
- Deterministic console guidance for the skip path
- Focused tests proving the new fail-closed preflight behavior
- No fallback modes
- No scope expansion beyond US-AUTO-57

=== FILE: 04_review_checklist.md ===
## Scope Validation
- APPROVE only if changed files are limited to:
  - `automation/scripts/run_story.sh`
  - `automation/scripts/_helpers.sh`
  - `tests/test_run_story.py`
- REJECT if any review-stage script, analyze script, registry file, bundle artifact, ledger file, or unrelated test file is changed.
- REJECT if the implementation adds telemetry, analyze enforcement, stage-loop escalation, artifact reuse, or lightweight review refresh behavior.
- REJECT if the implementation expands beyond preflight rerun-skip detection.

## Functional Validation
- APPROVE only if `run_story.sh` can block a rerun before Codex execution when sameness is conservatively proven.
- APPROVE only if the skip path is fail-closed and deterministic.
- APPROVE only if ordinary rerun behavior remains intact when proof is absent or uncertain.
- REJECT if the implementation skips reruns on guesswork, stale evidence, malformed evidence, or ambiguous comparisons.
- REJECT if the implementation changes manual-finish continuation semantics, review-stage semantics, or committed-HEAD boundary semantics.

## Verification
- Run focused verification for the touched scope, including the relevant `tests/test_run_story.py` coverage.
- Confirm that the skip path does not invoke Codex.
- Confirm that deterministic operator guidance is emitted on the skip path.
- Confirm that uncertainty falls through to normal run behavior.
- Confirm that no forbidden files were changed.

### HARD BLOCK
- REJECT if any forbidden file changed.
- REJECT if any fail-open skip path exists.
- REJECT if the implementation relies on non-committed or workspace-only state as proof of sameness.
- REJECT if the change weakens or bypasses existing pipeline invariants.
- Binary decision only:
  - APPROVE
  - REJECT

=== FILE: 05_followups.md ===
## Follow-Up Prompt Queue
- US-AUTO-31 — mandatory analyze gate before rerun or next phase
- US-AUTO-58 — stage-loop cap and forced escalation threshold
- US-AUTO-60 — lightweight review-evidence refresh without full rerun
- US-AUTO-30 — safe review-artifact reuse eligibility
- US-AUTO-61 — workflow telemetry registry for run stages, blockers, manual interventions, and timings

## Iteration Notes
- This story intentionally addresses only early rerun prevention, not later-stage decision enforcement.
- If implementation pressure suggests changing analyze semantics or stage-loop behavior, stop and leave that work to the follow-up stories above.
- Keep the proof rule conservative and narrowly tied to existing committed-head evidence.
- Registry logic to apply after successful bundle preparation:
  - selected next story remains `US-AUTO-57`
  - status should become `Bundle Drafted`
  - `US-AUTO-56` remains closed as `Implemented`
- No additional decomposition is required because the current story remains atomic.

=== FILE: 06_manual_actions.md ===
## Required Human Actions
1. Save this bundle pack to:
   `automation/bundle_packs/US-AUTO-57.bundle.md`

2. Materialize the bundle.
   Local:
   `automation/scripts/materialize_story_bundle.sh US-AUTO-57`

3. Validate the materialized bundle.
   Local:
   `automation/scripts/validate_story_bundle.sh US-AUTO-57`

4. Create the feature branch.
   Local:
   `git checkout -b feat/us-auto-57-rerun-skip-detection`

5. Commit the story artifacts through the canonical handoff flow.
   Local:
   `automation/scripts/commit_story_artifacts.sh US-AUTO-57`

6. Run the story implementation.
   Local:
   `automation/scripts/run_story.sh US-AUTO-57`

7. Analyze the resulting run using the fresh run directory produced by the current HEAD.
   Local:
   `automation/scripts/analyze_story_run.sh US-AUTO-57`

8. Before any future push or PR creation, explicitly discard ledger-only dirtiness if it is the only unintended workspace change.
   Local:
   `git restore automation/story_change_ledger.jsonl`

## Completion Status
- Story selected: US-AUTO-57
- Atomicity check: passed
- Bundle status: drafted
- Registry follow-up: pending human update after materialize and validate
- Implementation status: not started