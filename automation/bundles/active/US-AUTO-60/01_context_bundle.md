## Story ID and Title

US-AUTO-60 — Implementation freeze and review-evidence refresh without Codex rerun

## Source of Truth

Primary registry:

- docs/90_codex/epics/US-AUTO_REGISTRY.md

Current bundle pack:

- automation/bundle_packs/US-AUTO-60.bundle.md

Materialized active bundle:

- automation/bundles/active/US-AUTO-60/

Operator guide:

- docs/90_codex/US_AUTO_OPERATOR_GUIDE.md

Relevant scripts:

- automation/scripts/run_story.sh
- automation/scripts/analyze_story_run.sh
- automation/scripts/review_story_run.sh
- automation/scripts/ai_review_story_run.sh
- automation/scripts/classify_review_story_run.sh
- automation/scripts/review_gate_story_run.sh

Possible new script:

- automation/scripts/refresh_review_evidence.sh

Relevant tests:

- tests/test_analyze_story_run.py
- tests/test_review_story_run.py
- tests/test_ai_review_story_run.py
- tests/test_classify_review_story_run.py
- tests/test_review_gate_story_run.py
- tests/test_run_story.py
- tests/test_run_codex_task.py
- tests/test_refresh_review_evidence.py

## Current Code Reality

The US-AUTO pipeline is intentionally fail-closed.

Important existing invariants:

- review-stage must consume committed-HEAD evidence;
- dirty tree blocks review-stage;
- after a new commit, old `AUTOMATION_RUN_DIR` must not be reused for normal review-stage;
- `analyze_story_run.sh` receives only `STORY_ID` as a positional argument;
- run directory is provided through `AUTOMATION_RUN_DIR`;
- manual-finish continuation is a special allowed path only after the specific non-converging rerun boundary;
- active bundles are generated runtime artifacts and must not be manually edited;
- bundle packs are the story authoring source of truth.

US-AUTO-77 added a clearer `OPERATOR DECISION:` section in analyze output, but during execution it exposed a higher-priority blocker:

The pipeline lacks an explicit way to freeze an accepted implementation and refresh review evidence without invoking Codex again.

Without this path, the operator can get trapped:

1. Codex implementation is accepted.
2. Rerun is needed for fresh committed-HEAD evidence.
3. Rerun invokes adds non-essential polish.
5. Working tree becomes dirty.
6. Commit creates a new HEAD and invalidates previous run evidence.
7. Restore can make artifacts stale or fidelity-blocked.
8. Rerun repeats the same pattern.

US-AUTO-60 must create a safe escape hatch that preserves evidence fidelity but stops implementation churn.

## Architectural Intent

US-AUTO-60 should introduce an explicit freeze boundary.

The operator must be able to say:

- implementation is accepted;
- no more Codex implementation edits should be generated;
- regenerate only review evidence for the current committed HEAD.

This must not become a general bypass.

The refresh path should be treated as a review-evidence producer, not an implementation producer.

Preferred model:

1. Operator commits accepted implementation.
2. Operator confirms tree is clean.
3. Operator runs a refresh command for the story.
4. The refresh command computes the current review surface from committed git state.
5. The refresh command writes a run/evidence directory with clear metadata.
6. The analyzer verifies the refreshed evidence.
7. Review/classify/gate consume it like a pinned run only if all fidelity checks pass.

The refresh output should include enough metadata to support fail-closed checks:

- story_id;
- current_head;
- base_ref or merge-base;
- current_branch;
- refresh_mode;
- codex_invoked false;
- generated_at;
- changed_files path;
- diff.patch path;
- validation notes.

Do not invent a loose cache.

Do not mark arbitrary old artifacts as refreshed.

Do not skip diff regeneration.

Do not accept workspace state.

## Required Safety Properties

The refresh path must reject:

- running on `main`;
- dirty working tree;
- missing story ID;
- missing committed HEAD;
- missing or invalid active bundle;
- missing review-surface evidence;
- stale refreshed evidence after HEAD changes;
- story mismatch;
- manually edited active bundle drift if existing validators detect it;
- any path that would require Codex to generate implementation.

The refresh path must not:

- invoke `codex exec`;
- mutate implementation files;
- modify bundle files except through normal story authoring flow;
- silently update registry;
- silently run review/classify/gate;
- weaken existing gates.

## Risks

Main risk:

- creating a fail-open review bypass that allows stale or incomplete evidence.

Specific risks:

- treating a no-Codex refresh as if it were a full story run without metadata;
- allowing review-stage when HEAD changed after refresh;
- allowing refresh with dirty tree;
- allowing refresh on main;
- bypassing manual-finish continuation rules;
- accidentally changing semantic projection / companion-filter behavior;
- masking review-fidelity failures instead of regenerating evidence;
- making the operator think story is closed before PR merge and registry closeout.

Mitigations:

- fail closed;
- add explicit metadata;
- add targeted tests;
- make analyzer aware of refresh mode;
- require clean tree and non-main branch;
- preserve existing downstream checks;
- document the operator path and anti-patterns.

## Acceptance Notes

The story should be accepted if it adds a narrow, explicit no-Codex review-evidence refresh path and proves through tests that stale/dirty/main cases are rejected.

The story should be rejected if it solves the loop by weakening stale-run checks, dirty-tree checks, review-fidelity checks, or by making ordinary `run_story.sh` skip implementation work implicitly.

The story should also be rejected if it drifts into US-AUTO-58 loop caps, US-AUTO-31 analyze enforcement, US-AUTO-74 centralization, telemetry, or business features.

## Relationship To Next Stories

US-AUTO-60 is the first blocker after US-AUTO-77.

After US-AUTO-60:

- US-AUTO-58 should add loop cap / forced escalation threshold.
- US-AUTO-31 should enforce mandatory analyze gate before rerun or next phase.
- US-AUTO-74 should resume centralization only after freeze/loop-safety line is resolved or explicitly parked.

