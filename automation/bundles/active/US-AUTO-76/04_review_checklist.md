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

