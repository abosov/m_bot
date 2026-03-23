# STORY EXECUTION CHECKLIST

## Purpose
Stable SOP for running one user story through the Codex workflow with minimal risk and clear traceability.

## Standard Flow
1. Create a story branch before any commit.
2. Read mandatory context docs:
   - `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
   - `docs/90_codex/PROJECT_CONTEXT.md`
   - `docs/90_codex/REPOSITORY_MAP.md`
   - `docs/90_codex/PROJECT_CONTEXT_UPDATE_PROTOCOL.md`
3. Reconstruct repository map for the story scope (entry points, owners, nearby tests, docs).
4. Identify source of truth for architecture/data/process and write it into the bundle.
5. Define the Atomic Task Isolation contract for the story: one purpose, explicit intent, explicit out-of-scope statement, and hard-stop conditions.
6. Define `FILES_ALLOWED_TO_CHANGE` and explicit forbidden files for this story.
7. Make sure the bundle separates current-story work from future follow-up work before prompt drafting.
8. Confirm the relevant epic registry entry already exists, or create/update it before bundle drafting so the story has epic-level lifecycle tracking.
9. Bootstrap a bundle pack scaffold (`automation/scripts/new_story_bundle.sh <STORY-ID> "<Story Title>"`).
10. Resolve bundle pack content in `automation/bundle_packs/<STORY-ID>.bundle.md` (no unresolved placeholders).
11. Materialize active bundle files (`automation/scripts/materialize_story_bundle.sh <STORY-ID>`).
12. Validate the materialized bundle (`automation/scripts/validate_story_bundle.sh <STORY-ID>`).
13. Commit the story artifacts handoff (`automation/scripts/commit_story_artifacts.sh <STORY-ID>`).
   This step may stage and commit only:
   - `automation/bundle_packs/<STORY-ID>.bundle.md`
   - `automation/bundles/active/<STORY-ID>/**`
   The handoff must fail when no eligible story-artifact changes exist.
   The handoff must fail closed when any unrelated dirty path exists elsewhere in the repo, excluding only the exact ephemeral ledger path `automation/story_change_ledger.jsonl`.
   The commit message must stay deterministic: `chore(story): commit story artifacts for <STORY-ID> before run`.
14. Execute Codex run against the master prompt (`automation/scripts/run_story.sh <STORY-ID>` or runner direct).
   Default runner behavior uses lean story context.
   Runner execution is isolated in a temporary detached git worktree created from current branch `HEAD` and cleaned up on exit.
   Every run must generate `repository_map_runtime.md` before Codex execution and inject that repository map into the runtime Codex prompt.
   The runtime repository map must include architecture layers, story-local file-scope context from the active bundle when present, explicit allowed/forbidden scope parse status, anti-hallucination rules, and pipeline dependency hints.
   Story-local scope constraints in that runtime map must be marked as loaded when the allowed-file scope parses from `02_file_scope.md`; missing or unparseable allowed-file scope data must be surfaced as unavailable rather than implied to be empty, and a missing forbidden-file list must remain explicitly unavailable instead of being implied to be empty.
   Any tracked or regular untracked file changes produced inside that isolated worktree must be materialized back into the primary checkout before pytest and artifact collection; if materialization does not reach the primary checkout, the run must fail explicitly.
   After changed-files collection, the runner must enforce `02_file_scope.md` with the allowed-files guard before pytest and downstream review continue.
   Use `automation/run_codex_task.sh --full-context <master-prompt-path>` only when the story needs the full bundle context.
   `automation/scripts/run_story.sh <STORY-ID>` continues to use the runner defaults.
   Before execution, confirm the prompt explicitly contains intent, out-of-scope, allowed-files, forbidden-files, a statement that Atomic Task Isolation is mandatory for this run, hard-stop, follow-up capture language, a requirement to restate the one-sentence task intent before edits, and an execution gate that tells Codex to refuse non-atomic or underspecified prompts or prompts that batch another independently reviewable change.
   `run_story.sh` should record one evidence-only `story_started` event for `automation/story_change_ledger.jsonl`, and treat that exact path as ephemeral workflow state rather than implementation diff.
   `run_story.sh` and `automation/run_codex_task.sh` should restore the same exact path on exit so ledger writes do not persist as happy-path implementation drift.
   When the primary checkout is clean before execution begins, `automation/run_codex_task.sh` owns the rollback lifecycle for the whole run: capture the baseline before repository-visible writes, arm rollback immediately after that capture, and disarm it only after the final success gate.
   Any failed or interrupted run from that clean baseline must restore tracked files to the captured `HEAD` state and remove run-owned untracked artifacts, including automation run directories created for the failed attempt.
   If automatic rollback itself fails, the runner must exit non-zero and print an explicit rollback failure instead of allowing the run to appear successful.
   `run_story.sh` must refuse to continue when the requested story artifacts are still dirty and must print the deterministic remediation command `automation/scripts/commit_story_artifacts.sh <STORY-ID>`.
   `run_story.sh` must not auto-commit story artifacts.
15. Verify the Codex output stayed within the declared atomic task, implemented only one independently reviewable purpose, and captured any out-of-scope findings as follow-up work instead of inline changes.
16. Run required tests (minimum: targeted `pytest` scope for changed behavior).
17. Collect implementation and review artifacts into the story bundle.
   Review evidence is derived from the materialized primary checkout state rooted at the `origin/main` merge-base so committed and newly materialized working-tree changes are both captured before cleanup.
18. Resolve the latest review artifacts for the story (`automation/scripts/review_story_run.sh <STORY-ID>`).
   Review can proceed only when the current branch working tree is clean (commit-consistent with review evidence), excluding only the exact ephemeral ledger path `automation/story_change_ledger.jsonl`.
   If the working tree is dirty with materialized changes, inspect and commit first; then rerun story execution if needed.
   The review summary prints the canonical pinned inspection helper (`AUTOMATION_RUN_DIR=<run-dir> automation/scripts/analyze_story_run.sh <STORY-ID>`) plus the deterministic pinned gate command for that same run.
   The review summary must use the exact selected run directory for both printed commands so operators can continue deterministically from that run.
   Use the printed deterministic resume command (`AUTOMATION_RUN_DIR=<run-dir> automation/scripts/review_gate_story_run.sh <STORY-ID>`) when chaining directly into gate execution for that same run.
19. Execute and persist the AI review result for the latest run (`automation/scripts/ai_review_story_run.sh <STORY-ID>`).
20. Execute and persist the review classification result for the latest run (`automation/scripts/classify_review_story_run.sh <STORY-ID>`).
   The classification artifact must contain an exact standalone `MERGE RECOMMENDATION: approve` or `MERGE RECOMMENDATION: reject` line for the gate.
   If classification text is malformed or ambiguous, preserve `review_classification.md` for debugging and fail closed instead of deleting the artifact.
21. Execute the review gate for the latest run (`automation/scripts/review_gate_story_run.sh <STORY-ID>`).
   The gate must fail closed before AI review/classification when the current branch working tree has uncommitted changes outside the exact ephemeral ledger path `automation/story_change_ledger.jsonl`.
   The gate must also fail closed when the selected run's manifest HEAD does not match the current checkout HEAD; stale pre-finalize approval is never merge-valid.
   The gate must fail closed when review artifacts are not faithful to the authoritative branch diff reconstructed from the run manifest `review_artifact_base` and current checkout `HEAD`.
   Fidelity enforcement compares the selected run's `changed_files.txt` and `diff.patch` against regenerated git outputs for `review_artifact_base..HEAD`; any mismatch is a deterministic reject.
   Operator recovery path: inspect and commit materialized changes, rerun `automation/scripts/run_story.sh <STORY-ID>` if needed, then rerun gate.
   The gate resolves the latest run once, reuses that exact run directory for AI review and classification, writes `review_gate_result.json`, and must exit non-zero when the final decision is `reject` or cannot be derived from the classification artifact.
   `review_gate_result.json` must record both the reviewed HEAD from the run manifest and the current checkout HEAD used by the gate decision.
   Missing, invalid, or ambiguous `MERGE RECOMMENDATION:` output must be treated as a fail-closed reject.
   The gate artifact must distinguish malformed classification output from a classification step that failed before producing an artifact.
   The gate should append evidence-only ledger entries for `review_outcome` and, when rejected, `story_rejected`.
22. Use `automation/scripts/analyze_story_run.sh <STORY-ID>` when you need a read-only summary of the latest run artifacts, pytest state, review pipeline state, and recommended next operator action.
   By default the command inspects the latest run directory under `automation/runs/<STORY-ID>/`.
   Operators may also point it at a specific run with `AUTOMATION_RUN_DIR=automation/runs/<STORY-ID>/<RUN-ID> automation/scripts/analyze_story_run.sh <STORY-ID>`.
   The command must report a deterministic workflow chaining/resume section with:
   - current stage,
   - latest valid stage,
   - resume safety (`safe` or `blocked`),
   - exact next recommended command.
   The canonical resumable stage sequence is `run_artifacts_ready` -> `ai_review_completed` -> `classification_approved` -> `review_gate_passed`.
   Reject, invalid, stale, failed, or dirty conditions must remain explicit `blocked_*` states rather than being treated as resumable stages.
   Resume commands should pin `AUTOMATION_RUN_DIR` to the selected run directory for deterministic continuation, and downstream scripts must accept both absolute and repository-relative pinned run paths.
   The command is intentionally read-only and should be the first inspection step for missing artifacts, incomplete review stages, or gate failures.
23. Run follow-up prompts for merge blockers and accepted improvements.
   Decompose review output before execution so each follow-up prompt remains atomic, addresses exactly one review finding or one narrowly defined blocker, reuses the original scope boundaries unless explicitly changed, and captures any new out-of-scope findings as separate follow-up work.
   Each follow-up prompt must declare exactly one target finding/blocker identifier from the review artifacts; if more than one target is needed, split before execution.
   Before execution, confirm the follow-up prompt contains an explicit statement that Atomic Task Isolation is mandatory for the follow-up run, explicitly says follow-up mode is not an exception path around that contract, includes an execution gate that refuses implementation if more than one finding/blocker is present or if required isolation fields are missing, and requires Codex to restate the exact one-sentence follow-up intent before edits.
24. Re-run tests after follow-up changes.
25. Prepare PR with scope, risks, verification, docs impact, and any deferred follow-up tasks.
26. Update the epic registry when the story status changes, when a split/follow-up story is created, and when the latest outcome changes the epic-level picture.
27. Finalize the story with `automation/scripts/finalize_story.sh [PR_NUMBER]` after checks and review approvals pass.
   Finalization should append one evidence-only `story_finalized` entry when the story ID can be resolved from the finalized branch/ref.
   `finalize_story.sh` should restore the ephemeral ledger path on exit so happy-path finalization is clean.
28. Before merge/finalization, synchronize the epic registry row with the actual story outcome, including any new follow-up, split, cancelled, or superseded state.
29. The finalization script must merge with `gh pr merge --squash`, switch to local `main`, run `git pull --ff-only origin main`, and delete the merged story branch locally/remotely.
30. If scripted finalization cannot complete, stop and fix the blocking condition instead of finishing cleanup manually without documenting it.
31. Append process improvement notes for the completed story.

## Required Completion Artifacts
- Story bundle directory with context, scope, master prompt, review checklist, follow-ups, and manual actions.
- Commit history that includes the deterministic story-artifact handoff commit when bundle pack or active-bundle files changed before execution.
- Mandatory run artifacts including `manifest.md`, `story_context.md`, and `repository_map_runtime.md`.
- `repository_map_runtime.md` must capture architecture layers, story-local scope constraints plus allowed/forbidden parse status, anti-hallucination rules, and pipeline dependency hints for the run.
- When active-bundle allowed-file scope data is missing or unparseable, `repository_map_runtime.md` must mark story scope constraints as unavailable instead of rendering them as an empty allow/block list.
- When the forbidden-file list is absent from bundle scope data, `repository_map_runtime.md` must render it as unavailable rather than as an empty blocked list.
- Test evidence (`pytest` command set and result status).
- Durable AI review output artifact for the reviewed run.
- Durable review classification output artifact for the reviewed run.
  The classification artifact must include an exact standalone `MERGE RECOMMENDATION:` line with `approve` or `reject`.
- Durable review gate result artifact for the reviewed run (`review_gate_result.json`).
  The artifact must include machine-readable `decision`, `status`, and `decision_source` fields.
- Ephemeral workflow ledger artifact path (`automation/story_change_ledger.jsonl`).
  The ledger must remain append-only and may record `story_started`, `review_outcome`, `story_rejected`, and `story_finalized`, but it must not decide whether a story may continue in this workflow story.
- Follow-up capture for any out-of-scope finding discovered during implementation or review.
- Epic registry row updated to reflect the committed story outcome and any created follow-up/split story IDs.
- PR description linked to the story bundle.

### Story Change Ledger Evidence

- Treat `automation/story_change_ledger.jsonl` as an append-only workflow evidence stream with an ephemeral path contract (automation may restore it to `HEAD` so it does not appear as implementation drift in happy-path runs).
- Every ledger line must remain valid single-line JSON that downstream automation can parse with standard JSON tooling.
- Ledger evidence is considered durable for downstream consumers only when explicitly persisted outside the ephemeral path cleanup contract.
- Scripts must not rely on implicit self-committing behavior for ledger durability.
- Before merge/finalize decisions, verify the branch is in a committed state consistent with the reviewed run artifacts.

## Failure Stops
Stop and revise before merge if any condition is true:
- Bundle pack is not materialized from `automation/bundle_packs/<STORY-ID>.bundle.md`.
- Bundle validation fails (missing file, empty file, unresolved canonical placeholder token, or missing required section).
- Missing allowed/forbidden file scope.
- Missing Atomic Task Isolation contract, explicit out-of-scope statement, or follow-up capture for newly discovered out-of-scope work.
- Missing explicit requirement for Codex to restate the one-sentence task or follow-up intent before editing.
- Missing execution-gate language telling Codex to refuse non-atomic or underspecified prompts.
- Missing language stating that follow-up prompts cannot batch a second independently reviewable fix under follow-up mode.
- Follow-up prompt bundles multiple fixes, cleanup items, or architecture changes under one run without an explicit new scope definition.
- Review produced multiple independent findings, but follow-up work was not split into separate atomic prompts.
- Missing source-of-truth statement.
- Scope drift beyond the bundle.
- Tests not executed or failing without explicit waiver.
- Docs/process contradictions with `docs/90_codex/CODEX_OPERATING_SYSTEM.md`.
- Epic registry missing, stale, or inconsistent with the actual story outcome.

## Branch Lifecycle Rules

Each story bundle must be executed in its own git branch.

Workflow:

1. Create branch:
   git checkout -b feature/us-example-123-short-name
   Example pattern: git checkout -b <type>/<story-id>-<short-name>

2. Run Codex and perform all commits inside that branch.

3. Open PR and finalize through `automation/scripts/finalize_story.sh [PR_NUMBER]`.

4. The script must:

   gh pr checks <pr> --required
   gh pr merge <pr> --squash --delete-branch
   git checkout main
   git pull --ff-only origin main
   git branch -D <story-branch>

5. Remote branch deletion must also be enforced by the script.

Final expected local state:

* main

No additional branches must remain locally after a story is completed.
