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
6. Create or update story bundle in `automation/bundles/active/<STORY-ID>/`.
7. Generate a master prompt from template and lock scope/non-goals.
8. Execute Codex run against the master prompt.
   Default runner behavior uses lean story context.
   Runner execution is isolated in a temporary detached git worktree created from current branch `HEAD` and cleaned up on exit.
   Every run must generate `repository_map_runtime.md` before Codex execution and inject that repository map into the runtime Codex prompt.
   Any tracked or regular untracked file changes produced inside that isolated worktree must be materialized back into the primary checkout before pytest and artifact collection; if materialization does not reach the primary checkout, the run must fail explicitly.
   Use `automation/run_codex_task.sh --full-context <master-prompt-path>` only when the story needs the full bundle context.
   `automation/scripts/run_story.sh <STORY-ID>` continues to use the runner defaults.
9. Run required tests (minimum: targeted `pytest` scope for changed behavior).
10. Collect implementation and review artifacts into the story bundle.
   Review evidence is derived from the materialized primary checkout state rooted at the `origin/main` merge-base so committed and newly materialized working-tree changes are both captured before cleanup.
11. Resolve the latest review artifacts for the story (`automation/scripts/review_story_run.sh <STORY-ID>`).
12. Execute and persist the AI review result for the latest run (`automation/scripts/ai_review_story_run.sh <STORY-ID>`).
13. Execute and persist the review classification result for the latest run (`automation/scripts/classify_review_story_run.sh <STORY-ID>`).
14. Run follow-up prompts for merge blockers and accepted improvements.
15. Re-run tests after follow-up changes.
16. Prepare PR with scope, risks, verification, and docs impact.
17. Merge after checks and review approvals pass.
18. Resync local `main` (`git checkout main && git pull --ff-only`).
19. Delete merged story branch locally/remotely.
20. Append process improvement notes for the completed story.

## Required Completion Artifacts
- Story bundle directory with context, scope, master prompt, review checklist, follow-ups, and manual actions.
- Mandatory run artifacts including `manifest.md`, `story_context.md`, and `repository_map_runtime.md`.
- Test evidence (`pytest` command set and result status).
- Durable AI review output artifact for the reviewed run.
- Durable review classification output artifact for the reviewed run.
- PR description linked to the story bundle.

## Failure Stops
Stop and revise before merge if any condition is true:
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

3. Open PR and merge into main.

4. After merge:

   git checkout main
   git pull --ff-only
   git branch -d <story-branch>

5. Remote branch must also be deleted.

Final expected local state:

* main

No additional branches must remain locally after a story is completed.
