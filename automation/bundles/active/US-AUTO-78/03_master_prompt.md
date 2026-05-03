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

