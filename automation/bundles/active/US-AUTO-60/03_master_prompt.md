## Story ID and Title

US-AUTO-60 — Implementation freeze and review-evidence refresh without Codex rerun

## Role

You are working as architect, developer, QA, security reviewer, and technical writer for the Zumbot US-AUTO automation pipeline.

## Goal

Implement US-AUTO-60 with a narrow, fail-closed scope.

Add an explicit implementation-freeze / review-evidence refresh path that lets the operator refresh review evidence for the current committed HEAD without invoking Codex again.

The path must break the Codex polish rerun loop without weakening committed-HEAD, pinned-run, dirty-tree, stale-evidence, manual-finish, review, classification, or gate invariants.

## Source of Truth

Use these files as source of truth:

- docs/90_codex/epics/US-AUTO_REGISTRY.md
- docs/90_codex/US_AUTO_OPERATOR_GUIDE.md
- automation/bundle_packs/US-AUTO-60.bundle.md
- automation/bundles/active/US-AUTO-60/00_story.md
- automation/bundles/active/US-AUTO-60/01_context_bundle.md
- automation/bundles/active/US-AUTO-60/02_file_scope.md
- automation/bundles/active/US-AUTO-60/04_review_checklist.md

Respect existing behavior in:

- automation/scripts/run_story.sh
- automation/scripts/analyze_story_run.sh
- automation/scripts/review_story_run.sh
- automation/scripts/ai_review_story_run.sh
- automation/scripts/classify_review_story_run.sh
- automation/scripts/review_gate_story_run.sh
- automation/run_codex_task.sh

## Files Allowed To Change

automation/scripts/refresh_review_evidence.sh

automation/scripts/analyze_story_run.sh

automation/scripts/review_story_run.sh

automation/scripts/ai_review_story_run.sh

automation/scripts/classify_review_story_run.sh

automation/scripts/review_gate_story_run.sh

automation/run_codex_task.sh

tests/test_refresh_review_evidence.py

tests/test_analyze_story_run.py

tests/test_review_story_run.py

tests/test_ai_review_story_run.py

tests/test_classify_review_story_run.py

tests/test_review_gate_story_run.py

docs/90_codex/US_AUTO_OPERATOR_GUIDE.md

docs/90_codex/epics/US-AUTO_REGISTRY.md

automation/bundle_packs/US-AUTO-60.bundle.md

automation/bundles/active/US-AUTO-60/

## Files Not Allowed To Change

Business runtime code.

Database migrations.

OAuth scopes.

Calendar scopes.

Telegram bot runtime behavior.

Unrelated documentation.

Unrelated tests.

Do not implement US-AUTO-58.

Do not implement US-AUTO-31.

Do not implement US-AUTO-74.

Do not implement telemetry.

Do not implement deterministic pytest selection.

## Required Work

Create a no-Codex review-evidence refresh path.

Preferred implementation:

- add `automation/scripts/refresh_review_evidence.sh`;
- this script accepts a `STORY_ID`;
- it runs only from a non-main branch;
- it requires clean working tree;
- it validates the active story bundle exists;
- it computes the current committed review surface;
- it writes a run/evidence directory under `automation/runs/<STORY_ID>/<timestamp-or-refresh-id>`;
- it writes `changed_files.txt`;
- it writes `diff.patch`;
- it writes metadata, for example `refresh_review_evidence.json`;
- metadata must include:
  - story_id;
  - current_head;
  - current_branch;
  - base_ref or merge_base;
  - refresh_mode;
  - codex_invoked false;
  - generated_at;
  - evidence paths;
- it must not call `codex exec`;
- it must not modify implementation files.

If an existing run directory format must be reused, preserve compatibility with downstream scripts and add the minimum metadata needed to distinguish refresh mode.

Update `analyze_story_run.sh` so it can safely recognize the refreshed evidence.

Analyzer behavior must include:

- valid refreshed evidence for current HEAD may be review-stage eligible;
- stale refreshed evidence after a new commit must be blocked;
- dirty tree must block review-stage;
- missing metadata must fail closed;
- story mismatch must fail closed;
- operator decision must clearly explain whether to:
  - run no-Codex refresh;
  - use refreshed evidence for review-stage;
  - reject stale evidence and refresh again;
  - stop because tree is dirty;
  - stop because branch is main;
  - use normal run path instead.

Update downstream review-stage scripts only if required.

Downstream behavior must preserve:

- committed-HEAD checks;
- pinned evidence checks;
- stale evidence rejection;
- fail-closed review artifact handling;
- existing manual-finish continuation rules.

Add tests.

Required test coverage:

- no-Codex refresh succeeds on clean feature branch with committed HEAD;
- refresh refuses dirty working tree;
- refresh refuses main branch;
- refresh metadata contains `codex_invoked false`;
- refresh metadata records current HEAD;
- analyzer allows review-stage for valid refreshed evidence;
- analyzer rejects stale refreshed evidence after HEAD changes;
- analyzer keeps dirty-tree blocker;
- downstream review/classify/gate can consume valid refreshed evidence if scripts were changed;
- normal run behavior remains unchanged;
- no test is weakened to hide a regression.

Update `docs/90_codex/US_AUTO_OPERATOR_GUIDE.md`.

The guide must document:

- when implementation freeze is appropriate;
- when it is forbidden;
- the refresh command;
- the required preconditions;
- the correct analyze command after refresh;
- that refresh does not close the story;
- that review-stage still requires clean tree and valid pinned evidence;
- that after any new commit, old refreshed evidence is stale;
- that normal `run_story.sh` remains the implementation path;
- that no-Codex refresh is not a business-feature shortcut.

## Mandatory Safety Constraints

Do not invoke Codex in the refresh path.

Do not make `run_story.sh` silently choose refresh mode.

Do not allow refresh on `main`.

Do not allow refresh with dirty tree.

Do not allow refreshed evidence after HEAD changes.

Do not accept missing metadata.

Do not accept story mismatch.

Do not bypass AI review, classification, or gate.

Do not modify tests to weaken external behavior contracts.

Do not broaden scopes.

Do not add database migrations.

Do not edit active bundle manually.

## Output

Return:

- changed files;
- implementation summary;
- tests run;
- whether Codex is invoked in refresh path;
- how stale evidence is rejected;
- how dirty tree is rejected;
- how main branch is rejected;
- whether any downstream scripts were changed and why;
- follow-up recommendations for US-AUTO-58, US-AUTO-31, and US-AUTO-74.

Do not claim the story is closed.

Story closure happens only after PR merge, cleanup, main update, and registry closeout.

