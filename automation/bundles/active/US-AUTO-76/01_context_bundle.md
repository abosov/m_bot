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

