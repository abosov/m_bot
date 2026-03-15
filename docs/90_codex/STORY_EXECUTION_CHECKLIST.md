# STORY EXECUTION CHECKLIST

## Purpose
Stable SOP for running one user story through the Codex workflow with minimal risk and clear traceability.

## Standard Flow
1. Create a story branch before any commit (`git checkout -b <story-id>-<short-name>`).
2. Read mandatory context docs:
   - `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
   - `docs/90_codex/PROJECT_CONTEXT.md`
   - `docs/90_codex/REPOSITORY_MAP.md`
   - `docs/90_codex/PROJECT_CONTEXT_UPDATE_PROTOCOL.md`
3. Reconstruct repository map for the story scope (entry points, owners, nearby tests, docs).
4. Identify source of truth for architecture/data/process and write it into the bundle.
5. Define `FILES_ALLOWED_TO_CHANGE` and explicit forbidden files for this story.
6. Bootstrap a bundle pack scaffold (`automation/scripts/new_story_bundle.sh <STORY-ID> "<Story Title>"`).
7. Resolve bundle pack content in `automation/bundle_packs/<STORY-ID>.bundle.md` (no unresolved placeholders).
8. Materialize active bundle files (`automation/scripts/materialize_story_bundle.sh <STORY-ID>`).
9. Validate the materialized bundle (`automation/scripts/validate_story_bundle.sh <STORY-ID>`).
10. Execute Codex run against the master prompt (`automation/scripts/run_story.sh <STORY-ID>` or runner direct).
   Default runner behavior uses lean story context.
   Runner execution is isolated in a temporary detached git worktree created from current branch `HEAD` and cleaned up on exit.
   Every run must generate `repository_map_runtime.md` before Codex execution and inject that repository map into the runtime Codex prompt.
   The runtime repository map must include architecture layers, story-local file-scope context from the active bundle when present, explicit scope parse status, anti-hallucination rules, and pipeline dependency hints.
   Story-local scope constraints in that runtime map must be marked as loaded only when the allowed-file scope parses from `02_file_scope.md`; missing or unparseable scope data must be surfaced as unavailable rather than implied to be empty, and a missing forbidden-file list must remain explicitly unavailable instead of being implied to be empty.
   Any tracked or regular untracked file changes produced inside that isolated worktree must be materialized back into the primary checkout before pytest and artifact collection; if materialization does not reach the primary checkout, the run must fail explicitly.
   After changed-files collection, the runner must enforce `02_file_scope.md` with the allowed-files guard before pytest and downstream review continue.
   Use `automation/run_codex_task.sh --full-context <master-prompt-path>` only when the story needs the full bundle context.
   `automation/scripts/run_story.sh <STORY-ID>` continues to use the runner defaults.
11. Run required tests (minimum: targeted `pytest` scope for changed behavior).
12. Collect implementation and review artifacts into the story bundle.
   Review evidence is derived from the materialized primary checkout state rooted at the `origin/main` merge-base so committed and newly materialized working-tree changes are both captured before cleanup.
13. Resolve the latest review artifacts for the story (`automation/scripts/review_story_run.sh <STORY-ID>`).
14. Execute and persist the AI review result for the latest run (`automation/scripts/ai_review_story_run.sh <STORY-ID>`).
15. Execute and persist the review classification result for the latest run (`automation/scripts/classify_review_story_run.sh <STORY-ID>`).
   The classification artifact must contain an exact standalone `MERGE RECOMMENDATION: approve` or `MERGE RECOMMENDATION: reject` line for the gate.
   If classification text is malformed or ambiguous, preserve `review_classification.md` for debugging and fail closed instead of deleting the artifact.
16. Execute the review gate for the latest run (`automation/scripts/review_gate_story_run.sh <STORY-ID>`).
   The gate resolves the latest run once, reuses that exact run directory for AI review and classification, writes `review_gate_result.json`, and must exit non-zero when the final decision is `reject` or cannot be derived from the classification artifact.
   Missing, invalid, or ambiguous `MERGE RECOMMENDATION:` output must be treated as a fail-closed reject.
   The gate artifact must distinguish malformed classification output from a classification step that failed before producing an artifact.
17. Run follow-up prompts for merge blockers and accepted improvements.
18. Re-run tests after follow-up changes.
19. Prepare PR with scope, risks, verification, and docs impact.
20. Finalize the story with `automation/scripts/finalize_story.sh [PR_NUMBER]` after checks and review approvals pass.
21. The finalization script must merge with `gh pr merge --squash`, switch to local `main`, run `git pull --ff-only origin main`, and delete the merged story branch locally/remotely.
22. If scripted finalization cannot complete, stop and fix the blocking condition instead of finishing cleanup manually without documenting it.
23. Append process improvement notes for the completed story.

## Required Completion Artifacts
- Story bundle directory with context, scope, master prompt, review checklist, follow-ups, and manual actions.
- Mandatory run artifacts including `manifest.md`, `story_context.md`, and `repository_map_runtime.md`.
- `repository_map_runtime.md` must capture architecture layers, story-local scope constraints plus parse status, anti-hallucination rules, and pipeline dependency hints for the run.
- When active-bundle allowed-file scope data is missing or unparseable, `repository_map_runtime.md` must mark story scope constraints as unavailable instead of rendering them as an empty allow/block list.
- When the forbidden-file list is absent from bundle scope data, `repository_map_runtime.md` must render it as unavailable rather than as an empty blocked list.
- Test evidence (`pytest` command set and result status).
- Durable AI review output artifact for the reviewed run.
- Durable review classification output artifact for the reviewed run.
  The classification artifact must include an exact standalone `MERGE RECOMMENDATION:` line with `approve` or `reject`.
- Durable review gate result artifact for the reviewed run (`review_gate_result.json`).
  The artifact must include machine-readable `decision`, `status`, and `decision_source` fields.
- PR description linked to the story bundle.

## Failure Stops
Stop and revise before merge if any condition is true:
- Bundle pack is not materialized from `automation/bundle_packs/<STORY-ID>.bundle.md`.
- Bundle validation fails (missing file, empty file, unresolved canonical placeholder token, or missing required section).
- Missing allowed/forbidden file scope.
- Missing source-of-truth statement.
- Scope drift beyond the bundle.
- Tests not executed or failing without explicit waiver.
- Docs/process contradictions with `docs/90_codex/CODEX_OPERATING_SYSTEM.md`.


## Branch Lifecycle Rules

Each story bundle must be executed in its own git branch.

Workflow:

1. Create branch:
   git checkout -b <type>/<story-id>-<short-name>

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
