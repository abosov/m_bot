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

