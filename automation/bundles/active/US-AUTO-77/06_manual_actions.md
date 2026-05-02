## Story ID and Title

US-AUTO-77 — Operator workflow simplification and decision model

## Required Human Actions

Before materialize, run locally from the repository root:

git status --short && git branch --show-current

Expected:

- branch is feat/us-auto-77-operator-workflow-simplification;
- working tree is clean except the newly created or modified bundle pack before commit.

Materialize:

automation/scripts/materialize_story_bundle.sh US-AUTO-77

Validate:

automation/scripts/validate_story_bundle.sh US-AUTO-77

Inspect generated files:

find automation/bundles/active/US-AUTO-77 -maxdepth 1 -type f -print

Open files in Cursor:

open -a "Cursor" automation/bundle_packs/US-AUTO-77.bundle.md
open -a "Cursor" automation/bundles/active/US-AUTO-77/00_story.md
open -a "Cursor" automation/bundles/active/US-AUTO-77/03_master_prompt.md

Commit bundle artifacts:

git status --short
git add automation/bundle_packs/US-AUTO-77.bundle.md automation/bundles/active/US-AUTO-77
git commit -m "docs(us-auto): add US-AUTO-77 story bundle"

Run story locally on the feature branch, not on main.

After run completes, do not jump directly to review-stage.

First analyze.

Use only STORY_ID as positional argument.

Correct analyze shape:

AUTOMATION_RUN_DIR=automation/runs/US-AUTO-77/<RUN_DIR> automation/scripts/analyze_story_run.sh US-AUTO-77

Wrong analyze shape:

automation/scripts/analyze_story_run.sh US-AUTO-77 automation/runs/US-AUTO-77/<RUN_DIR>

Before review-stage, check:

git status --short

If dirty tree exists, resolve it first.

If only automation/story_change_ledger.jsonl is dirty and it is unintended ledger-only dirtiness, run:

git restore automation/story_change_ledger.jsonl

Run targeted tests locally:

python3 -m pytest tests/test_analyze_story_run.py

If review-stage semantics are touched, also run:

python3 -m pytest tests/test_review_story_run.py tests/test_ai_review_story_run.py tests/test_classify_review_story_run.py tests/test_review_gate_story_run.py

After implementation and tests pass:

git status --short

Then add only intended files and commit:

git add docs/90_codex/US_AUTO_OPERATOR_GUIDE.md automation/scripts/analyze_story_run.sh tests/test_analyze_story_run.py docs/90_codex/README.md docs/90_codex/epics/US-AUTO_REGISTRY.md
git commit -m "US-AUTO-77: Add operator workflow decision model"

If some optional files were not changed, omit them from git add.

After any new commit, previous AUTOMATION_RUN_DIR is invalid.

Run the story again or follow the explicit manual-finish continuation contract if analyze says that is the valid path.

Do not reuse a stale run for review-stage.

Before review-stage:

git status --short
git rev-parse HEAD

Then analyze the pinned committed-head run:

AUTOMATION_RUN_DIR=automation/runs/US-AUTO-77/<RUN_DIR> automation/scripts/analyze_story_run.sh US-AUTO-77

Only continue if analyze says review-stage is allowed and tree is clean.

Push current branch:

git pushup

Create PR with gh according to project workflow.

Do not mark story closed after PR creation.

Do not mark story closed immediately after merge.

After implementation PR is merged, run locally:

git checkout main && git pull --ff-only origin main

Clean branches according to project workflow.

Then check registry:

open -a "Cursor" docs/90_codex/epics/US-AUTO_REGISTRY.md

Update US-AUTO-77 only after merge:

- Status: Implemented;
- PR number;
- pinned run;
- note that operator guide and decision model were added.

Commit registry closeout in a separate branch/PR if current workflow requires it.

Only after registry closeout is merged or explicitly confirmed not required may US-AUTO-74 begin.

## Completion Status

Not complete at bundle creation time.

Completion requires:

1. bundle materialized;
2. bundle validated;
3. bundle artifacts committed;
4. implementation completed;
5. targeted tests passed;
6. story run completed;
7. analyze completed with AUTOMATION_RUN_DIR;
8. review-stage completed only with clean tree and valid pinned run;
9. classification and gate passed;
10. implementation PR merged;
11. branch cleanup completed;
12. main updated locally;
13. registry closeout checked and completed.

