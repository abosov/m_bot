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

