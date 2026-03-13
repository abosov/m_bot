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
8. Execute Codex run against the master prompt (direct path or `automation/scripts/run_story.sh <STORY-ID>`).
9. Run required tests (minimum: targeted `pytest` scope for changed behavior).
10. Collect implementation and review artifacts into the story bundle.
11. Classify findings using `docs/90_codex/REVIEW_CLASSIFICATION_RULES.md`.
12. Run follow-up prompts for merge blockers and accepted improvements.
13. Re-run tests after follow-up changes.
14. Prepare PR with scope, risks, verification, and docs impact.
15. Merge after checks and review approvals pass.
16. Resync local `main` (`git checkout main && git pull --ff-only`).
17. Delete merged story branch locally/remotely.
18. Append process improvement notes for the completed story.

## Required Completion Artifacts
- Story bundle directory with context, scope, master prompt, review checklist, follow-ups, and manual actions.
- Test evidence (`pytest` command set and result status).
- Review classification output (blockers/minor/follow-up story).
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
