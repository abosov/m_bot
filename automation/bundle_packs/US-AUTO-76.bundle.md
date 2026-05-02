Story-ID: US-AUTO-76
Title: Classifier scope semantics for governance story artifacts

=== FILE: 00_story.md ===
## Story ID and Title

US-AUTO-76 — Classifier scope semantics for governance story artifacts

## Objective

Teach the review classification layer to treat approved story governance artifacts as valid story workflow artifacts instead of merge blockers, when and only when they are explicitly approved by the story scope and belong to the active story workflow.

The immediate problem is that a technically complete story can still be rejected because the classifier treats normal governance artifacts as out-of-scope implementation changes, for example:

- `automation/bundle_packs/<STORY_ID>.bundle.md`
- `automation/bundles/active/<STORY_ID>/**`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

The target behavior is not to weaken review safety. Runtime and implementation files must still be validated separately. This story only clarifies classifier/review-gate semantics for intentional story governance artifacts.

## Scope

Implement narrow classifier and review-gate semantics for governance story artifacts.

Allowed story governance artifacts:

- bundle pack source-of-truth:
  - `automation/bundle_packs/<STORY_ID>.bundle.md`
- materialized active bundle output:
  - `automation/bundles/active/<STORY_ID>/**`
- lifecycle/governance registry update:
  - `docs/90_codex/epics/US-AUTO_REGISTRY.md`

These files may be treated as allowed story artifacts only when:

1. the bundle pack is the source-of-truth artifact for the same story ID;
2. the active bundle path belongs to the same story ID;
3. the registry update is an intentional lifecycle/governance update;
4. the files are explicitly present in the story scope;
5. implementation/runtime review surface remains separately validated.

Expected implementation surface:

- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- tests that exercise classifier and review-gate behavior for governance artifacts

Expected test surface:

- `tests/test_classify_review_story_run.py`
- `tests/test_review_gate_story_run.py`

Story artifact surface:

- `automation/bundle_packs/US-AUTO-76.bundle.md`
- `automation/bundles/active/US-AUTO-76/**`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Non-goals

Do not rewrite the review pipeline.

Do not implement operator workflow simplification.

Do not create or modify `docs/90_codex/US_AUTO_OPERATOR_GUIDE.md`.

Do not add `automation/scripts/next_step.sh`.

Do not centralize duplicated semantic projection logic.

Do not centralize companion-filter logic.

Do not refactor downstream scripts beyond the minimal classifier/review-gate change needed for this story.

Do not modify semantic projection producer behavior.

Do not change pinned run / HEAD safety checks.

Do not change stage-loop policy.

Do not reduce or bypass runtime review validation.

Do not fix regressions by weakening tests or changing external error/message contracts unless the story explicitly documents that as the intended contract change.

## Dependencies

US-AUTO-75 must already be merged.

The current roadmap refresh must already be merged into `main`.

US-AUTO-76 must start from a clean feature branch created from fresh `main`.

US-AUTO-77 must not start until US-AUTO-76 is resolved or explicitly parked.

US-AUTO-74 must not start until US-AUTO-76 and US-AUTO-77 are resolved or explicitly parked.

## Source of Truth

Primary source of truth:

- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/US-AUTO-76.bundle.md`
- `automation/bundles/active/US-AUTO-76/**`

Behavioral source of truth:

- US-AUTO-75 established semantic projection and projection-aware review surface behavior.
- US-AUTO-76 only changes classifier/review-gate interpretation of approved governance/story artifacts.
- Runtime review surface must remain independently validated.

Required workflow source of truth:

- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/scripts/commit_story_artifacts.sh`
- `automation/scripts/run_story.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`

## Current Code Reality

Several downstream review scripts already contain local story-artifact filtering logic.

The current classifier can still interpret normal governance artifacts as out-of-scope changes and produce a merge-blocking rejection even when the implementation/runtime review surface is valid.

Known problematic artifact categories:

- `automation/bundle_packs/<STORY_ID>.bundle.md`
- `automation/bundles/active/<STORY_ID>/**`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

This was observed after US-AUTO-75: the implementation was complete, but the remaining reject was a classifier scope-semantics limitation rather than a runtime correctness blocker.

The current implementation likely has path filters in multiple scripts. This story must avoid broad centralization work and change only the minimum needed classifier/review-gate semantics.

## Target Outcome

A story run that changes only approved story governance artifacts plus valid implementation files must not be classified as a merge blocker solely because the governance artifacts are present.

The classifier should clearly distinguish:

- approved story governance artifacts;
- implementation/runtime review surface;
- genuinely out-of-scope changes.

The review gate should respect the classifier’s improved distinction without weakening safety gates.

Expected result:

- governance artifacts for the active story are allowed when explicitly scope-approved;
- unrelated bundle packs, unrelated active bundle directories, and unrelated registry changes remain suspicious or blocking;
- implementation/runtime files remain separately validated;
- tests prove the intended behavior and protect against regression.

=== FILE: 01_context_bundle.md ===
## Source of Truth

US-AUTO-76 is a narrow follow-up after US-AUTO-75.

US-AUTO-75 delivered semantic projection review fidelity and made the runtime implementation complete, but the pipeline still produced a reject caused by classifier scope semantics around governance/story artifacts.

The story source of truth is the following rule:

Story governance artifacts are allowed when:

1. bundle pack is the source-of-truth artifact;
2. active bundle is materialized output;
3. registry update is an intentional lifecycle/governance update;
4. these files are explicitly scope-approved;
5. implementation/runtime review surface remains separately validated.

The repository workflow source of truth is:

- `automation/bundle_packs/US-AUTO-76.bundle.md`
- `automation/bundles/active/US-AUTO-76/**`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/scripts/commit_story_artifacts.sh`
- `automation/scripts/run_story.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`

## Current Code Reality

The pipeline has several review-stage scripts with related but not fully unified filtering behavior.

The likely implementation area is:

- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`

The likely test area is:

- `tests/test_classify_review_story_run.py`
- `tests/test_review_gate_story_run.py`

Known current issue:

- approved governance artifacts can be interpreted as out-of-scope and cause a merge-blocking classification;
- this makes the operator manually decide whether a reject is real or merely a governance-artifact false positive;
- this increases friction immediately before business-feature work.

Important current invariant:

- do not run review/gate against stale run artifacts;
- after any new commit, previous `AUTOMATION_RUN_DIR` is invalid;
- sequence remains run → commit → rerun → analyze → review;
- review-stage commands must be based on pinned run and committed HEAD.

## Architectural Intent

The classifier should treat story governance artifacts as a separate category from runtime implementation files.

The review gate should not treat approved governance artifacts as runtime out-of-scope drift.

The classifier should fail closed for ambiguous or unrelated governance artifacts.

The intended distinction:

Allowed governance artifacts for the active story:

- `automation/bundle_packs/<STORY_ID>.bundle.md`
- `automation/bundles/active/<STORY_ID>/**`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md` when explicitly scope-approved

Not allowed by this story:

- bundle packs for another story;
- active bundle directories for another story;
- registry changes when not explicitly scope-approved;
- unrelated docs or automation changes;
- broad wildcard acceptance of all `automation/bundle_packs/**` or `automation/bundles/active/**`.

The classifier should keep a conservative model:

- recognize approved story governance artifacts;
- keep unrelated artifacts suspicious;
- preserve implementation/runtime review validation.

## Risks

Risk: over-permissive path filtering.

Mitigation: tests must cover wrong-story bundle packs and wrong-story active bundles as not automatically allowed.

Risk: hiding implementation drift behind governance artifact allowance.

Mitigation: implementation/runtime files must remain separately classified and reviewed.

Risk: accidentally starting US-AUTO-77 operator simplification.

Mitigation: do not modify operator guide or next-step automation.

Risk: accidentally starting US-AUTO-74 centralization.

Mitigation: avoid helper centralization across all downstream scripts; make the minimum focused change in classifier/review-gate semantics.

Risk: changing external CLI contracts.

Mitigation: preserve current command names, output shape, exit-code intent, and existing tests unless a change is explicitly required by US-AUTO-76.

Risk: repeating the US-AUTO-75 rejection cycle.

Mitigation: add targeted regression tests proving that active story governance artifacts are not merge blockers when explicitly scope-approved.

## Acceptance Notes

Acceptance requires all of the following:

1. `automation/scripts/materialize_story_bundle.sh US-AUTO-76` succeeds.
2. `automation/scripts/validate_story_bundle.sh US-AUTO-76` succeeds.
3. Story artifacts are committed before running the story.
4. Targeted classifier/review-gate tests pass.
5. Full relevant local test selection passes.
6. `automation/scripts/run_story.sh US-AUTO-76` completes.
7. After the run, do not reuse stale run directories after any commit.
8. `automation/scripts/analyze_story_run.sh US-AUTO-76 <latest-run-dir>` confirms the next allowed stage.
9. Classifier no longer blocks solely because approved US-AUTO-76 governance artifacts are present.
10. Genuinely unrelated governance artifacts remain blocked or suspicious.

=== FILE: 02_file_scope.md ===
## Files Allowed To Change

Primary implementation files:

- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`

Primary test files:

- `tests/test_classify_review_story_run.py`
- `tests/test_review_gate_story_run.py`

Story governance artifacts:

- `automation/bundle_packs/US-AUTO-76.bundle.md`
- `automation/bundles/active/US-AUTO-76/00_story.md`
- `automation/bundles/active/US-AUTO-76/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-76/02_file_scope.md`
- `automation/bundles/active/US-AUTO-76/03_master_prompt.md`
- `automation/bundles/active/US-AUTO-76/04_review_checklist.md`
- `automation/bundles/active/US-AUTO-76/05_followups.md`
- `automation/bundles/active/US-AUTO-76/06_manual_actions.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

Optional only if directly required by existing test organization:

- no additional files by default

## Files Not Allowed To Change

Do not change:

- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/run_story.sh`
- `automation/scripts/commit_story_artifacts.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/scripts/new_story_bundle.sh`
- `automation/scripts/escalate_story.sh`
- `automation/scripts/finalize_story.sh`
- `automation/story_change_ledger.jsonl`
- `docs/90_codex/US_AUTO_OPERATOR_GUIDE.md`
- `automation/scripts/next_step.sh`
- unrelated files under `docs/**`
- unrelated files under `automation/bundle_packs/**`
- unrelated files under `automation/bundles/active/**`

Do not change tests to weaken existing behavior.

Do not modify tests in a way that removes or dilutes external contract expectations.

Do not change broad pipeline behavior outside classifier/review-gate semantics.

Do not edit materialized active bundle files manually after materialization; update the bundle pack and re-materialize instead.

=== FILE: 03_master_prompt.md ===
## Role

You are working as a senior automation pipeline developer for the Zumbot / US-AUTO AI-dev workflow.

Your task is to implement US-AUTO-76 narrowly and safely.

You must preserve existing safety invariants and avoid starting adjacent stories.

## Goal

Fix classifier/review-gate scope semantics so approved story governance artifacts are not treated as merge blockers solely because they are governance artifacts.

The intended allowed governance artifact rule is:

Story governance artifacts are allowed when:

1. bundle pack is the source-of-truth artifact;
2. active bundle is materialized output;
3. registry update is an intentional lifecycle/governance update;
4. these files are explicitly scope-approved;
5. implementation/runtime review surface remains separately validated.

You must implement this without weakening review of runtime implementation files.

## Source of Truth

Use these files as the story source of truth:

- `automation/bundle_packs/US-AUTO-76.bundle.md`
- `automation/bundles/active/US-AUTO-76/00_story.md`
- `automation/bundles/active/US-AUTO-76/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-76/02_file_scope.md`
- `automation/bundles/active/US-AUTO-76/03_master_prompt.md`
- `automation/bundles/active/US-AUTO-76/04_review_checklist.md`
- `automation/bundles/active/US-AUTO-76/05_followups.md`
- `automation/bundles/active/US-AUTO-76/06_manual_actions.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

Use the existing code reality from:

- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `tests/test_classify_review_story_run.py`
- `tests/test_review_gate_story_run.py`

## Files Allowed To Change

You may change:

- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `tests/test_classify_review_story_run.py`
- `tests/test_review_gate_story_run.py`
- `automation/bundle_packs/US-AUTO-76.bundle.md`
- `automation/bundles/active/US-AUTO-76/**`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Files Not Allowed To Change

Do not change:

- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/run_story.sh`
- `automation/scripts/commit_story_artifacts.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/scripts/new_story_bundle.sh`
- `automation/scripts/escalate_story.sh`
- `automation/scripts/finalize_story.sh`
- `automation/story_change_ledger.jsonl`
- `docs/90_codex/US_AUTO_OPERATOR_GUIDE.md`
- `automation/scripts/next_step.sh`
- unrelated bundle packs
- unrelated active bundle directories
- unrelated docs

## Output

Implement the smallest safe change that satisfies the story.

Expected implementation behavior:

1. Active-story bundle pack path is recognized as an approved governance artifact:
   - `automation/bundle_packs/<STORY_ID>.bundle.md`

2. Active-story materialized bundle directory is recognized as approved governance output:
   - `automation/bundles/active/<STORY_ID>/**`

3. Registry update can be recognized as approved lifecycle/governance update only when explicitly scope-approved:
   - `docs/90_codex/epics/US-AUTO_REGISTRY.md`

4. Wrong-story governance artifacts are not automatically allowed:
   - `automation/bundle_packs/<OTHER_STORY>.bundle.md`
   - `automation/bundles/active/<OTHER_STORY>/**`

5. Implementation/runtime files remain separately validated and cannot hide behind governance artifact semantics.

6. Tests must prove:
   - active-story governance artifacts do not create classifier merge blockers when scope-approved;
   - wrong-story governance artifacts still block or remain suspicious;
   - registry path allowance remains explicit and does not become a broad docs wildcard;
   - review gate respects the classifier semantics without weakening existing checks.

7. Preserve existing CLI behavior, exit-code expectations, and external output contracts unless the test explicitly documents the new US-AUTO-76 contract.

Do not change tests to make failures disappear. Fix the implementation.

=== FILE: 04_review_checklist.md ===
## Scope Validation

Confirm that only the following implementation files changed:

- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`

Confirm that only the following test files changed:

- `tests/test_classify_review_story_run.py`
- `tests/test_review_gate_story_run.py`

Confirm that story artifacts changed only for US-AUTO-76:

- `automation/bundle_packs/US-AUTO-76.bundle.md`
- `automation/bundles/active/US-AUTO-76/**`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

Confirm that no adjacent scope was started:

- no operator guide changes;
- no `next_step.sh`;
- no semantic projection centralization;
- no companion-filter centralization;
- no stage-loop policy work;
- no failure-summary UX work;
- no unrelated docs changes.

Confirm there are no unintended workspace changes:

- `automation/story_change_ledger.jsonl` must not be committed unless explicitly required by the workflow.
- `.DS_Store` files must not be committed.
- unrelated local bundle artifacts must not be committed.

## Functional Validation

Classifier behavior:

- approved active-story bundle pack is not a merge blocker by itself;
- approved active-story materialized bundle files are not merge blockers by themselves;
- explicitly approved registry update is not a merge blocker by itself;
- wrong-story bundle pack remains blocked or suspicious;
- wrong-story active bundle remains blocked or suspicious;
- unrelated docs remain blocked or suspicious;
- runtime implementation files remain separately classified.

Review-gate behavior:

- review gate does not fail solely because approved governance artifacts exist;
- review gate still fails for true blockers;
- review gate still respects classifier output for out-of-scope runtime files;
- review gate still respects pinned run / committed HEAD assumptions.

Regression behavior:

- existing classifier tests continue to pass;
- existing review-gate tests continue to pass;
- no safety checks are removed;
- no broad wildcard allowance is introduced.

## Verification

Before running the story:

1. Materialize bundle:

   `automation/scripts/materialize_story_bundle.sh US-AUTO-76`

2. Validate bundle:

   `automation/scripts/validate_story_bundle.sh US-AUTO-76`

3. Review diff:

   `git diff -- automation/bundle_packs/US-AUTO-76.bundle.md automation/bundles/active/US-AUTO-76 docs/90_codex/epics/US-AUTO_REGISTRY.md`

4. Commit story artifacts:

   `automation/scripts/commit_story_artifacts.sh US-AUTO-76`

Then run targeted tests after implementation:

- `python3 -m pytest tests/test_classify_review_story_run.py tests/test_review_gate_story_run.py`

If related review-stage tests are affected, also run:

- `python3 -m pytest tests/test_ai_review_story_run.py tests/test_analyze_story_run.py tests/test_classify_review_story_run.py tests/test_review_gate_story_run.py tests/test_review_story_run.py`

Then run story workflow:

- `automation/scripts/run_story.sh US-AUTO-76`

After any new commit, do not reuse previous run directories.

After the story run completes, use the latest run directory from a fresh analyze output.

=== FILE: 05_followups.md ===
## Follow-Up Prompt Queue

Potential follow-up after US-AUTO-76:

1. US-AUTO-77 — Operator workflow simplification and decision model.
2. US-AUTO-74 — Centralize semantic projection and companion-filter contract.
3. US-AUTO-31 — Mandatory analyze gate before rerun or next phase.
4. US-AUTO-58 — Stage-loop cap and forced escalation threshold.

Do not start US-AUTO-77 until US-AUTO-76 is resolved or explicitly parked.

Do not start US-AUTO-74 until US-AUTO-76 and US-AUTO-77 are resolved or explicitly parked.

Do not revive US-AUTO-28 until US-AUTO-76, US-AUTO-77, and US-AUTO-58 clarify classifier semantics, operator decision flow, and stage-loop policy.

Do not revive US-AUTO-57 or US-AUTO-69 unless a concrete residual defect is revalidated.

## Iteration Notes

If classifier changes become broader than governance artifact semantics, stop and split the work.

If review-gate changes require touching analyze, ai_review, or review_story scripts, stop and reassess. That is likely US-AUTO-74 or another follow-up, not US-AUTO-76.

If operator-facing simplification becomes necessary, park it for US-AUTO-77.

If duplicated helper logic becomes painful during implementation, do not centralize in this story. Add a note for US-AUTO-74 instead.

If tests reveal that existing behavior is ambiguous, preserve fail-closed behavior for unknown or wrong-story paths.

If the classifier still rejects approved governance artifacts after implementation, collect the exact changed-file list and classifier output, then refine only the governance artifact classification logic.

=== FILE: 06_manual_actions.md ===
## Required Human Actions

Before implementation:

1. Confirm branch:

   `git branch --show-current`

   Expected:

   `feat/us-auto-76-governance-artifact-scope-semantics`

2. Confirm clean workspace except the new bundle pack if not yet committed:

   `git status --short`

3. Save this bundle pack to:

   `automation/bundle_packs/US-AUTO-76.bundle.md`

4. Materialize:

   `automation/scripts/materialize_story_bundle.sh US-AUTO-76`

5. Validate:

   `automation/scripts/validate_story_bundle.sh US-AUTO-76`

6. Open generated files in Cursor:

   `open -a "Cursor" automation/bundle_packs/US-AUTO-76.bundle.md automation/bundles/active/US-AUTO-76`

7. Review bundle diff:

   `git diff -- automation/bundle_packs/US-AUTO-76.bundle.md automation/bundles/active/US-AUTO-76`

8. Commit story artifacts before running the story:

   `automation/scripts/commit_story_artifacts.sh US-AUTO-76`

After implementation:

1. Run targeted tests:

   `python3 -m pytest tests/test_classify_review_story_run.py tests/test_review_gate_story_run.py`

2. Run broader review-stage tests if touched behavior requires it:

   `python3 -m pytest tests/test_ai_review_story_run.py tests/test_analyze_story_run.py tests/test_classify_review_story_run.py tests/test_review_gate_story_run.py tests/test_review_story_run.py`

3. Run story:

   `automation/scripts/run_story.sh US-AUTO-76`

4. Analyze latest run before review-stage commands.

5. Do not run review/gate commands against stale run artifacts after any commit.

6. If `automation/story_change_ledger.jsonl` is the only unintended dirty file before push or PR, discard it:

   `git restore automation/story_change_ledger.jsonl`

7. Before PR, confirm:

   `git status --short`

8. Create PR only after story workflow is resolved.

## Completion Status

US-AUTO-76 is complete only when:

- bundle materializes successfully;
- bundle validates successfully;
- story artifacts are committed;
- implementation and tests are committed;
- targeted tests pass;
- story workflow completes;
- analyze/review/classify/gate are resolved according to current pipeline rules;
- PR is opened, checked, merged, and branch cleanup is completed.

Do not proceed to US-AUTO-77 until US-AUTO-76 is merged or explicitly parked.
