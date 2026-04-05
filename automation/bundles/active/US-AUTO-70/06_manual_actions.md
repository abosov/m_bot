
## Required Human Actions

1. Where to perform: locally
2. Ensure the repository is clean and synchronized before materializing:
   `git status --short`
3. Save this bundle pack to:
   `automation/bundle_packs/US-AUTO-70.bundle.md`
4. Materialize the bundle:
   `automation/scripts/materialize_story_bundle.sh US-AUTO-70`
5. Validate the bundle:
   `automation/scripts/validate_story_bundle.sh US-AUTO-70`
6. Update the registry entry for US-AUTO-70 and related notes if the workflow expects a separate bundle-artifact commit.
7. If the existing branch `feat/us-auto-70-rerun-preflight-recompute` is the intended working branch, switch to it:
   `git checkout feat/us-auto-70-rerun-preflight-recompute`
8. If that branch is stale or incorrect, delete or rename it explicitly before recreating; do not continue ambiguously.
9. Commit bundle artifacts using the normal handoff workflow.
10. Run the story:
    `automation/scripts/run_story.sh US-AUTO-70`
11. After the run completes, first analyze the latest run and inspect workspace state before any review-stage command:
    `AUTOMATION_RUN_DIR=<latest-run-dir> automation/scripts/analyze_story_run.sh US-AUTO-70 && git status --short`
12. Follow the committed-HEAD/manual-finish workflow strictly. After any new commit, rerun the story and use the fresh latest run directory rather than reusing an older pinned run.
13. Proceed through review stages only after stage-gate invariants are satisfied.
14. Merge only after approve gate on the fresh committed-head run, then clean up branch and return to main.

## Completion Status

* Bundle prepared for materialize + validate.
* Story selected: US-AUTO-70.
* Story intent: stable filtered-baseline recomputation for rerun/review.
* Next operator step after saving bundle: materialize, validate, then switch to the existing intended feature branch if appropriate.
