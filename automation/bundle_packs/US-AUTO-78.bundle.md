Story-ID: US-AUTO-78
Title: Post-US-AUTO-60 registry roadmap and orchestration-line alignment

=== FILE: 00_story.md ===
## Story ID and Title

US-AUTO-78 — Post-US-AUTO-60 registry roadmap and orchestration-line alignment

## Objective

Update the US-AUTO epic registry and operator workflow documentation after US-AUTO-60 closed the implementation-freeze and no-Codex review-evidence refresh blocker.

This story realigns the stabilization roadmap around:

1. stage-loop control;
2. mandatory analyze decision-gate enforcement;
3. deterministic story-pipeline orchestration;
4. compact operator/AI decision handoff;
5. semantic projection / companion-filter centralization after the safety/orchestration line.

## Scope

This is a docs/governance-only story.

Allowed scope:

- update `docs/90_codex/epics/US-AUTO_REGISTRY.md`;
- update `docs/90_codex/US_AUTO_OPERATOR_GUIDE.md`;
- create this bundle pack;
- materialize the active bundle for US-AUTO-78.

The story may add planned registry rows for orchestration-line work, but must not implement those future runtime stories.

## Non-goals

- Do not change runtime automation scripts.
- Do not change `analyze_story_run.sh` behavior.
- Do not implement `advance_story.sh`.
- Do not add or modify tests.
- Do not implement US-AUTO-58, US-AUTO-31, US-AUTO-74, US-AUTO-79, or US-AUTO-80.
- Do not edit generated active bundle files manually after materialization.
- Do not broaden this into runtime pipeline behavior.

## Dependencies

- US-AUTO-60 is implemented and fully registry-closed.
- PR #274 merged implementation-freeze / no-Codex review-evidence refresh.
- PR #275 merged registry closeout for US-AUTO-60.
- Current repository state is clean except for this docs/governance story's planned documentation changes.
- No open PRs block this registry realignment.

## Source of Truth

- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `docs/90_codex/US_AUTO_OPERATOR_GUIDE.md`
- Existing committed evidence from PR #274 and PR #275.
- Current validator contract for story bundle packs.

## Current Code Reality

US-AUTO-60 is already implemented and registry-closed, but the registry still needed post-closeout roadmap realignment.

The registry previously kept the correct broad order of US-AUTO-58 → US-AUTO-31, but it did not yet explicitly place US-AUTO-79 and US-AUTO-80 before US-AUTO-74 or move US-AUTO-61/62 behind the core stage-control line.

The operator guide already described the normal workflow, but it needed the full stage pipeline expressed in the current canonical order and a clear distinction between deterministic next steps and decision-dependent stops.

Current working branch:

- `docs/us-auto-78-roadmap-orchestration-alignment`

Current intended changed files:

- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `docs/90_codex/US_AUTO_OPERATOR_GUIDE.md`
- `automation/bundle_packs/US-AUTO-78.bundle.md`
- `automation/bundles/active/US-AUTO-78/**`

## Target Outcome

The registry and operator guide clearly describe the post-US-AUTO-60 workflow strategy.

The registry must:

- stop describing US-AUTO-60 as an unresolved future blocker;
- record US-AUTO-60 as the closed freeze/refresh safety layer;
- update US-AUTO-77 notes to point to US-AUTO-58 and US-AUTO-31 as the remaining safety line;
- reframe US-AUTO-58 as stage-loop control across rerun and refresh/review/classify loops;
- reframe US-AUTO-31 as the mandatory analyze decision gate before any next phase;
- add planned orchestration-line entries after US-AUTO-31;
- keep US-AUTO-74 after the safety/orchestration line;
- keep US-AUTO-61 and US-AUTO-62 behind the core stage-control line;
- preserve the registry as portfolio-level source of truth, not story-level behavior duplication.

The operator guide must:

- describe the full story pipeline as `pre-story gate -> bundle pack -> materialize -> commit story artifacts -> run -> analyze -> optional refresh evidence -> ai_review -> classify -> gate -> PR -> merge -> cleanup -> registry closeout -> story closed`;
- distinguish deterministic next steps from decision-dependent stops;
- document rerun vs refresh vs follow-up policy;
- reinforce that PR merged is not story closed.

=== FILE: 01_context_bundle.md ===
## Relevant Background

The US-AUTO automation pipeline has been stabilized through a long sequence of fail-closed workflow stories.

Recent important completed stories include:

- US-AUTO-75 — additive review-fidelity projection contract;
- US-AUTO-76 — classifier/review-gate semantics for scope-approved governance artifacts;
- US-AUTO-77 — operator workflow simplification and decision model;
- US-AUTO-60 — implementation freeze and review-evidence refresh without Codex rerun.

US-AUTO-60 closed the blocker where accepted implementations could only refresh review evidence by invoking Codex again. It added a no-Codex refresh path and allowed continuation through analyze, AI review, classification, and review gate on pinned refresh-run artifacts.

## Source of Truth

Use these files as the source of truth for this story:

- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `docs/90_codex/US_AUTO_OPERATOR_GUIDE.md`
- `automation/bundle_packs/US-AUTO-78.bundle.md`

Use these completed PR facts as committed evidence:

- US-AUTO-60 implementation PR #274;
- US-AUTO-60 registry closeout PR #275;
- US-AUTO-77 implementation PR #272.

## Current Code Reality

The registry already contains the US-AUTO epic status table and roadmap.

The operator guide already exists and contains the normal workflow, analyze command contract, operator decision model, dirty tree handling, rerun rules, manual-finish continuation, review-stage path, and post-merge registry closure gate.

Before this story, the registry still contained stale or incomplete post-US-AUTO-60 framing:

- US-AUTO-60 appeared in some narrative as a future blocker;
- US-AUTO-77 notes still pointed to US-AUTO-60 as the follow-up blocker;
- the roadmap did not yet explicitly include the orchestration line needed for deterministic stage chaining;
- the current story process was not fully documented as a pipeline with deterministic vs decision-dependent transitions.

## Architectural Intent

This story is a portfolio-governance alignment story.

It does not change runtime behavior.

The intended architecture after this story is:

1. US-AUTO-60 is treated as the completed freeze/refresh safety layer.
2. US-AUTO-58 becomes the next stage-loop safety story.
3. US-AUTO-31 becomes the mandatory analyze decision-gate story.
4. US-AUTO-79 and US-AUTO-80 are planned as the orchestration and compact decision packet line.
5. US-AUTO-74 remains a later P1 maintainability cleanup for duplicated projection/filter/fidelity logic.

The registry should stay portfolio-level and must not duplicate full future story contracts.

The operator guide should describe the operational process clearly enough for current work, while marking future orchestration as planned rather than implemented.

## Risks

- Overstating future orchestration as already implemented.
- Letting registry content duplicate story-level implementation contracts.
- Accidentally changing runtime scripts or tests in a docs-only story.
- Losing the strict rule that PR merged is not story closed.
- Weakening committed-HEAD, pinned-run, refresh-run, review, classify, or gate safety invariants in documentation wording.
- Forgetting that US-AUTO-74 remains maintainability cleanup, not the immediate safety blocker.

## Acceptance Notes

The story is accepted when:

- the registry no longer describes US-AUTO-60 as an unresolved future blocker;
- the US-AUTO-77 note no longer says US-AUTO-60 is the follow-up blocker;
- US-AUTO-60 notes mention PR #274 and registry closeout PR #275;
- Next Recommended Story starts with US-AUTO-78 as this docs/governance alignment, then US-AUTO-58, US-AUTO-31, US-AUTO-79, US-AUTO-80, and US-AUTO-74;
- the operator guide includes the full story pipeline in the current canonical order, deterministic vs decision-dependent steps, and rerun vs refresh vs follow-up policy;
- only allowed files changed;
- bundle validation passes.

=== FILE: 02_file_scope.md ===
## Files Allowed To Change

- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `docs/90_codex/US_AUTO_OPERATOR_GUIDE.md`
- `automation/bundle_packs/US-AUTO-78.bundle.md`
- `automation/bundles/active/US-AUTO-78/**`

## Files Not Allowed To Change

- `automation/scripts/**`
- `automation/run_codex_task.sh`
- `tests/**`
- application/runtime bot code
- database migrations
- dependency files
- CI workflow files
- unrelated documentation

## Scope Notes

This is a governance/docs-only story.

No runtime behavior may change.

The registry may add new planned story rows for orchestration-line work, but must not duplicate detailed story-level contracts that belong in future bundle packs.

The active bundle files may only be produced by materialization. They must not be manually edited as the source of truth.

=== FILE: 03_master_prompt.md ===
## Role

You are implementing a docs/governance-only US-AUTO story in the Zumbot automation pipeline.

Act as:

1. architect;
2. workflow governance reviewer;
3. technical writer;
4. QA reviewer.

## Goal

Realign the US-AUTO registry and operator guide after US-AUTO-60 closed the implementation-freeze and no-Codex review-evidence refresh blocker.

The result must clearly define the post-US-AUTO-60 stabilization order and document the current story workflow process without changing runtime behavior.

## Source of Truth

Use these files as source of truth:

- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `docs/90_codex/US_AUTO_OPERATOR_GUIDE.md`
- `automation/bundle_packs/US-AUTO-78.bundle.md`

Use these committed facts:

- US-AUTO-60 implementation PR #274 is merged.
- US-AUTO-60 registry closeout PR #275 is merged.
- US-AUTO-77 implementation PR #272 is merged.
- US-AUTO-60 introduced `automation/scripts/refresh_review_evidence.sh`.
- US-AUTO-60 established the accepted-implementation freeze path.

## Files Allowed To Change

- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `docs/90_codex/US_AUTO_OPERATOR_GUIDE.md`
- `automation/bundle_packs/US-AUTO-78.bundle.md`
- `automation/bundles/active/US-AUTO-78/**`

## Files Not Allowed To Change

- `automation/scripts/**`
- `automation/run_codex_task.sh`
- `tests/**`
- application/runtime bot code
- database migrations
- dependency files
- CI workflow files
- unrelated documentation

## Task

Implement US-AUTO-78 by updating only the allowed documentation and story artifact files.

Required registry updates:

1. Remove or replace stale wording that describes US-AUTO-60 as a future unresolved blocker.
2. State that US-AUTO-60 is implemented and registry-closed through PR #274 and PR #275.
3. Update the active systemic blocker narrative:
   - the freeze/refresh blocker is closed;
   - remaining blockers are stage-loop governance and mandatory analyze-gate enforcement;
   - future orchestration should execute deterministic next steps automatically and stop with compact decision packets when a branch decision is required.
4. Update the optimization roadmap so the post-US-AUTO-60 order is:
   - US-AUTO-58;
   - US-AUTO-31;
   - US-AUTO-79;
   - US-AUTO-80;
   - US-AUTO-74;
   - US-AUTO-61/62 after core stage control.
5. Update the US-AUTO-77 table note so it no longer says US-AUTO-60 is the follow-up blocker.
6. Update the US-AUTO-60 table note so it records:
   - PR #274;
   - registry closeout PR #275;
   - `refresh_review_evidence.sh`;
   - the accepted-implementation freeze path;
   - the policy that accepted implementations should not invoke Codex rerun merely to refresh review evidence.
7. Add planned registry rows for:
   - `US-AUTO-79` — Story pipeline orchestrator for deterministic stage chaining.
   - `US-AUTO-80` — Compact operator/AI decision packet UX for non-deterministic stops.
8. Update `Next Recommended Story` so US-AUTO-58 comes after this registry realignment story, followed by US-AUTO-31, then the orchestration line, then US-AUTO-74.
9. Keep US-AUTO-74 as P1 maintainability cleanup after the safety/orchestration line.
10. Do not mark US-AUTO-58, US-AUTO-31, US-AUTO-74, US-AUTO-79, or US-AUTO-80 as implemented.

Required operator guide updates:

1. Add or update a section describing the full story pipeline:

   `pre-story gate -> bundle pack -> materialize -> commit story artifacts -> run -> analyze -> optional refresh evidence -> ai_review -> classify -> gate -> PR -> merge -> cleanup -> registry closeout -> story closed`

2. Add a section distinguishing deterministic vs decision-dependent steps:
   - deterministic safe next steps may be automated;
   - decision-dependent stops must print a compact operator/AI decision packet.

3. Add or update rerun vs refresh vs follow-up policy:
   - materially changed implementation requires rerun;
   - accepted implementation with stale evidence may use refresh evidence without Codex rerun;
   - explicit safety blockers may receive narrow fixes;
   - non-safety polish/preference rejects should become escalation/follow-up rather than implementation polishing.

4. Preserve existing committed-HEAD and pinned-run safety invariants.
5. Preserve the rule: PR merged is not story closed.

## Output

Expected output:

- updated `docs/90_codex/epics/US-AUTO_REGISTRY.md`;
- updated `docs/90_codex/US_AUTO_OPERATOR_GUIDE.md`;
- valid `automation/bundle_packs/US-AUTO-78.bundle.md`;
- materialized active bundle under `automation/bundles/active/US-AUTO-78/`.

Do not change runtime scripts, tests, application code, migrations, dependencies, or CI workflows.

Run documentation/scope validation only unless an unexpected non-doc file changes.

=== FILE: 04_review_checklist.md ===
## Scope Validation

- [ ] Only allowed files changed.
- [ ] No runtime scripts changed.
- [ ] No tests changed.
- [ ] No application/runtime code changed.
- [ ] No migrations changed.
- [ ] No dependency files changed.
- [ ] No CI workflow files changed.
- [ ] Active bundle files were generated by materialization, not manually edited as source of truth.

## Functional Validation

- [ ] Registry no longer describes US-AUTO-60 as an unresolved future blocker.
- [ ] US-AUTO-77 notes no longer point to US-AUTO-60 as the follow-up blocker.
- [ ] US-AUTO-60 notes record PR #274 and registry closeout PR #275.
- [ ] Registry preserves US-AUTO-58 as the next runtime/governance stabilization story.
- [ ] Registry places US-AUTO-31 after US-AUTO-58.
- [ ] Registry adds or clearly plans the orchestration line after US-AUTO-31.
- [ ] Registry keeps US-AUTO-74 after safety/orchestration work.
- [ ] Operator Guide describes the full story pipeline.
- [ ] Operator Guide distinguishes deterministic next steps from decision-dependent stops.
- [ ] Operator Guide documents rerun vs refresh vs follow-up policy.
- [ ] No future orchestration behavior is described as already implemented.

## Verification

Run:

    automation/scripts/validate_story_bundle.sh US-AUTO-78
    git diff -- docs/90_codex/epics/US-AUTO_REGISTRY.md docs/90_codex/US_AUTO_OPERATOR_GUIDE.md automation/bundle_packs/US-AUTO-78.bundle.md automation/bundles/active/US-AUTO-78
    git status --short

Expected result:

- bundle validation passes;
- changed files are limited to allowed scope;
- no runtime/test files changed.

=== FILE: 05_followups.md ===
## Follow-Up Prompt Queue

### US-AUTO-58

Implement stage-loop cap and forced escalation threshold across run/rerun/refresh/review/classify/fix loops.

This follow-up should explicitly account for the US-AUTO-60 refresh path so that the pipeline does not enter a new loop form:

`refresh -> review -> reject -> small fix -> amend -> refresh`

### US-AUTO-31

Make analyze the mandatory decision gate before rerun, refresh, review continuation, classification, gate, escalation, follow-up, or phase advance.

This follow-up may introduce or formalize a machine-readable `operator_decision.json` artifact if that is the cleanest way to support future orchestration.

### US-AUTO-79

Add a story pipeline orchestrator that executes deterministic safe next steps automatically.

Likely script name:

`automation/scripts/advance_story.sh`

The orchestrator should read the analyze decision output and continue only while the next action is deterministic and safe.

### US-AUTO-80

Add compact operator/AI decision packet UX for non-deterministic stops.

This may be folded into US-AUTO-79 if the implementation is small and atomic.

### US-AUTO-74

Resume semantic projection and companion-filter centralization only after US-AUTO-58, US-AUTO-31, and the orchestration decision model are resolved or explicitly parked.

## Iteration Notes

US-AUTO-78 exists because US-AUTO-60 changed the strategic state of the pipeline.

Before US-AUTO-60, the next blocker was the absence of implementation freeze and no-Codex review-evidence refresh.

After US-AUTO-60, that blocker is closed. The next work should focus on stage-loop control, mandatory analyze-gate enforcement, deterministic orchestration, and compact decision packet UX before resuming US-AUTO-74 maintainability cleanup or the US-AUTO-61/62 observability line.

=== FILE: 06_manual_actions.md ===
## Required Human Actions

Before starting this story, verify the pre-story gate:

    git status --short
    gh pr list --state open --json number,title,headRefName,baseRefName,url
    git branch --show-current

Expected:

- clean working tree or only intentional US-AUTO-78 docs/governance changes;
- no conflicting open PRs;
- current branch is `docs/us-auto-78-roadmap-orchestration-alignment`.

After creating this bundle pack, materialize and validate it:

    automation/scripts/materialize_story_bundle.sh US-AUTO-78
    automation/scripts/validate_story_bundle.sh US-AUTO-78

Review scope:

    git status --short
    git diff -- docs/90_codex/epics/US-AUTO_REGISTRY.md docs/90_codex/US_AUTO_OPERATOR_GUIDE.md automation/bundle_packs/US-AUTO-78.bundle.md automation/bundles/active/US-AUTO-78

Commit the docs/governance changes and story artifacts together.

Then run the story only if the bundle is valid and the working branch is not `main`:

    automation/scripts/run_story.sh US-AUTO-78

## Completion Status

Not complete until:

- bundle validates;
- allowed docs and story artifacts are committed;
- run/analyze/review path completes for this docs/governance story;
- PR is merged;
- branch cleanup is done;
- local `main` is updated;
- registry closeout is checked or explicitly deemed not required beyond this story's own registry update.
