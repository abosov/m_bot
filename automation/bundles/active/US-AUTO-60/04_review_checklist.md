## Story ID and Title

US-AUTO-60 — Implementation freeze and review-evidence refresh without Codex rerun

## Scope Validation

Confirm:

- A no-Codex review-evidence refresh path exists.
- The refresh path is explicit and operator-invoked.
- The refresh path does not call `codex exec`.
- The refresh path does not mutate implementation files.
- The refresh path refuses to run on `main`.
- The refresh path refuses dirty working tree.
- The refresh path records current HEAD.
- The refresh path records story ID.
- The refresh path records no-Codex refresh mode.
- The refresh path records `codex_invoked false`.
- The refresh path writes or refreshes review-surface evidence.
- The refresh path is fail-closed when required evidence cannot be generated.

Confirm analyzer behavior:

- Valid refreshed evidence for current HEAD can be recognized.
- Stale refreshed evidence after a new commit is rejected.
- Dirty tree still blocks review-stage.
- Story mismatch is rejected.
- Missing metadata is rejected.
- Operator decision explains the next safe action.
- Correct analyze command contract is preserved:
  - run dir through `AUTOMATION_RUN_DIR`;
  - only `STORY_ID` as positional argument.

Confirm downstream behavior:

- Review-stage can consume valid refreshed evidence only if fidelity checks pass.
- AI review behavior remains fail-closed.
- Classification behavior remains fail-closed.
- Review gate behavior remains fail-closed.
- Manual-finish continuation behavior is not weakened.
- Normal run behavior is not weakened.

Confirm no implementation changes were made to:

- business runtime code;
- database migrations;
- OAuth scopes;
- calendar scopes;
- telemetry;
- stage-loop cap;
- mandatory analyze gate enforcement;
- deterministic pytest selection;
- semantic projection centralization;
- companion-filter centralization.

## Functional Validation

Run targeted tests:

python3 -m pytest tests/test_refresh_review_evidence.py tests/test_analyze_story_run.py

If downstream scripts changed, also run:

python3 -m pytest tests/test_review_story_run.py tests/test_ai_review_story_run.py tests/test_classify_review_story_run.py tests/test_review_gate_story_run.py

If run preflight or Codex task runner changed, also run:

python3 -m pytest tests/test_run_story.py tests/test_run_codex_task.py

Expected behavior to verify manually if tests do not cover it fully:

1. On feature branch with clean tree, refresh command creates valid evidence.
2. On feature branch with dirty tree, refresh command fails.
3. On main branch, refresh command fails.
4. After refresh, analyze can inspect the refreshed run with:

AUTOMATION_RUN_DIR=automation/runs/US-AUTO-60/<RUN_DIR> automation/scripts/analyze_story_run.sh US-AUTO-60

5. After a new commit, the previous refreshed evidence is stale and review-stage is blocked.
6. Review-stage is allowed only with clean tree and valid current-HEAD evidence.

## Verification

Verification must include both automated targeted tests and manual contract checks.

Required automated validation:

- run `tests/test_refresh_review_evidence.py` if the new refresh script is introduced;
- run `tests/test_analyze_story_run.py`;
- run downstream review-stage tests if corresponding scripts changed;
- run run-preflight / Codex task-runner tests only if those files changed.

Required manual verification:

- refresh refuses `main`;
- refresh refuses dirty tree;
- refresh records current HEAD;
- refresh metadata says `codex_invoked false`;
- refreshed evidence becomes stale after a new commit;
- analyze uses `AUTOMATION_RUN_DIR` and only `STORY_ID` as positional argument;
- review-stage proceeds only when analyze says it is allowed.

## Regression Checks

Confirm existing external contracts are preserved:

- `analyze_story_run.sh` still accepts only `STORY_ID` as positional argument.
- `AUTOMATION_RUN_DIR` remains the run directory mechanism.
- Dirty tree blocks review-stage.
- New commit invalidates old run evidence.
- Manual-finish continuation remains narrow.
- Review/classify/gate remain fail-closed.
- Tests were not changed to permit weaker behavior.

## Security and Integrity Review

Confirm:

- no generated evidence path can escape `automation/runs/<STORY_ID>/`;
- story ID is validated or safely handled;
- metadata is deterministic enough for audit;
- no external credentials or secrets are read;
- no OAuth or calendar scopes are touched;
- no network operation is introduced for refresh;
- no arbitrary command injection is introduced through story ID;
- refresh path cannot silently overwrite unrelated story evidence.

## Documentation Review

Confirm `docs/90_codex/US_AUTO_OPERATOR_GUIDE.md` documents:

- implementation-freeze purpose;
- refresh command;
- allowed use cases;
- forbidden use cases;
- preconditions;
- stale evidence rule;
- dirty tree rule;
- main branch rule;
- analyze command after refresh;
- review-stage continuation after refresh;
- story closure rule.

## Completion Review

Before PR:

- branch is not `main`;
- working tree is clean;
- bundle pack is committed;
- active bundle was generated by materialize script;
- active bundle validates;
- implementation is committed;
- targeted tests pass;
- latest run/evidence corresponds to current HEAD;
- review-stage is run only after analyze says it is allowed.

After PR merge:

- checkout main;
- pull latest main;
- delete local branch if not already deleted;
- delete remote branch if not already deleted;
- check registry;
- update registry closeout if required;
- do not start US-AUTO-58 until US-AUTO-60 is closed or explicitly parked.

