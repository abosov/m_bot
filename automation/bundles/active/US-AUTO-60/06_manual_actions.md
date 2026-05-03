## Story ID and Title

US-AUTO-60 — Implementation freeze and review-evidence refresh without Codex rerun

## Required Human Actions

Before materialize, run locally from the repository root:

git status --short && git branch --show-current

Expected:

- branch is feat/us-auto-60-implementation-freeze-refresh;
- working tree contains only the newly created US-AUTO-60 bundle pack before commit.

Materialize:

automation/scripts/materialize_story_bundle.sh US-AUTO-60

Validate:

automation/scripts/validate_story_bundle.sh US-AUTO-60

Inspect generated files:

find automation/bundles/active/US-AUTO-60 -maxdepth 1 -type f -print

Open files in Cursor:

open -a "Cursor" automation/bundle_packs/US-AUTO-60.bundle.md
open -a "Cursor" automation/bundles/active/US-AUTO-60/00_story.md
open -a "Cursor" automation/bundles/active/US-AUTO-60/03_master_prompt.md

Commit bundle artifacts:

git status --short
git add automation/bundle_packs/US-AUTO-60.bundle.md automation/bundles/active/US-AUTO-60
git commit -m "docs(us-auto): add US-AUTO-60 story bundle"

Run story locally on the feature branch, not on main:

automation/scripts/run_story.sh US-AUTO-60

After run completes, do not jump directly to review-stage.

First analyze.

Use only STORY_ID as positional argument.

Correct analyze shape:

AUTOMATION_RUN_DIR=automation/runs/US-AUTO-60/<RUN_DIR> automation/scripts/analyze_story_run.sh US-AUTO-60

Wrong analyze shape:

automation/scripts/analyze_story_run.sh US-AUTO-60 automation/runs/US-AUTO-60/<RUN_DIR>

If implementation is accepted but Codex produced additional non-essential polish on rerun, use the new US-AUTO-60 freeze/refresh path only after it exists and only according to analyze/operator guidance.

Before any review-stage command, check:

git status --short
git rev-parse HEAD

If dirty tree exists, resolve it first.

If only `automation/story_change_ledger.jsonl` is dirty and it is unintended ledger-only dirtiness, run:

git restore automation/story_change_ledger.jsonl

Run targeted tests locally:

python3 -m pytest tests/test_refresh_review_evidence.py tests/test_analyze_story_run.py

If downstream review-stage scripts are touched, also run:

python3 -m pytest tests/test_review_story_run.py tests/test_ai_review_story_run.py tests/test_classify_review_story_run.py tests/test_review_gate_story_run.py

If run preflight or Codex task runner is touched, also run:

python3 -m pytest tests/test_run_story.py tests/test_run_codex_task.py

After implementation and tests pass:

git status --short

Then add only intended files.

Likely add set:

git add automation/scripts/refresh_review_evidence.sh automation/scripts/analyze_story_run.sh automation/scripts/review_story_run.sh automation/scripts/ai_review_story_run.sh automation/scripts/classify_review_story_run.sh automation/scripts/review_gate_story_run.sh automation/run_codex_task.sh tests/test_refresh_review_evidence.py tests/test_analyze_story_run.py tests/test_review_story_run.py tests/test_ai_review_story_run.py tests/test_classify_review_story_run.py tests/test_review_gate_story_run.py docs/90_codex/US_AUTO_OPERATOR_GUIDE.md docs/90_codex/epics/US-AUTO_REGISTRY.md

Omit unchanged optional files from `git add`.

Commit implementation:

git commit -m "US-AUTO-60: Add implementation freeze review evidence refresh"

After any new commit, previous `AUTOMATION_RUN_DIR` is invalid unless the new US-AUTO-60 refresh path creates fresh evidence for current HEAD and analyze explicitly accepts it.

Run the no-Codex refresh path according to the implemented command.

Expected shape if the preferred script name is used:

automation/scripts/refresh_review_evidence.sh US-AUTO-60

Then analyze the refreshed evidence:

AUTOMATION_RUN_DIR=automation/runs/US-AUTO-60/<REFRESH_RUN_DIR> automation/scripts/analyze_story_run.sh US-AUTO-60

Only continue if analyze says review-stage is allowed and tree is clean.

Run review-stage according to current workflow.

Do not rely only on a printed next recommended command.

Verify invariants first:

- clean tree;
- non-main branch;
- pinned evidence corresponds to current HEAD;
- analyzer says review-stage is allowed;
- no stale `AUTOMATION_RUN_DIR`.

Push current branch:

git pushup

Create PR with `gh` according to project workflow.

Do not mark story closed after PR creation.

Do not mark story closed immediately after merge.

After implementation PR is merged, run locally:

git checkout main && git pull --ff-only origin main

Clean branches according to project workflow.

Then check registry:

open -a "Cursor" docs/90_codex/epics/US-AUTO_REGISTRY.md

Update US-AUTO-60 only after merge:

- Status: Implemented;
- PR number;
- validation summary;
- note that implementation freeze + review-evidence refresh without Codex rerun was added.

Commit registry closeout in a separate branch/PR if current workflow requires it.

Only after registry closeout is merged or explicitly confirmed not required may US-AUTO-58 begin.

## Completion Status

Not complete at bundle creation time.

Completion requires:

1. bundle materialized;
2. bundle validated;
3. bundle artifacts committed;
4. implementation completed;
5. targeted tests passed;
6. no-Codex refresh path verified;
7. analyze completed with `AUTOMATION_RUN_DIR`;
8. review-stage completed only with clean tree and valid current-HEAD evidence;
9. classification and gate passed;
10. implementation PR merged;
11. branch cleanup completed;
12. main updated locally;
13. registry closeout checked and completed.
