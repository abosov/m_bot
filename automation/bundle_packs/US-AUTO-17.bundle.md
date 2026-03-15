# Story Bundle Pack
Story-ID: US-AUTO-17
Version: 1

This pack is the single source of truth for materialized story bundle files.

=== FILE: 00_story.md ===
# US-AUTO-17: Repository Map Injection v2

## Story ID and Title
- Story ID: `US-AUTO-17`
- Title: `Repository Map Injection v2`

## Objective
Strengthen Codex anti-hallucination context by upgrading the runtime repository map from a generic top-level overview into a story-aware architecture artifact with explicit layer boundaries, story-local file guidance, anti-hallucination rules, and dependency hints.

## Scope
- Extend `automation/run_codex_task.sh` so `repository_map_runtime.md` contains:
  - explicit architecture layer boundaries
  - a story-local context section for the active story
  - anti-hallucination rules for Codex
  - dependency hints for the automation pipeline
- Reuse existing bundle scope data from `automation/bundles/active/<STORY-ID>/02_file_scope.md` when building story-local repository context.
- Ensure generated `story_context.md` and `codex_prompt.md` continue to reference the runtime repository map artifact.
- Update focused tests for repository map generation and injection behavior.
- Update workflow documentation/checklists so Repository Map Injection v2 becomes part of the expected runner behavior.

## Non-goals
- Do not implement allowed-files enforcement changes in this story.
- Do not implement console UX improvements, chaining, resume, or long-wait logging in this story.
- Do not redesign AI review / classification / review gate.
- Do not change backend product runtime code.
- Do not introduce a heavy repository indexing system or non-deterministic scanning layer.

## Dependencies
- Existing bundle-pack + materialization workflow.
- Existing isolated worktree execution.
- Existing repository map injection baseline from `US-AUTO-11`.
- Existing story file-scope contract in active bundles.

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/40_ai/zumbot_codex/REPOSITORY_MAP.md`
- `docs/40_ai/zumbot_codex/PROJECT_CONTEXT.md`
- `automation/run_codex_task.sh`
- `automation/scripts/run_story.sh`
- `automation/scripts/validate_story_bundle.sh`
- `tests/test_run_codex_task.py`

## Current Code Reality
- `automation/run_codex_task.sh` already generates `repository_map_runtime.md`, injects it into `codex_prompt.md`, and records repository-map metadata in the run manifest.
- The current repository map is useful but still too generic: it lists top-level directories and curated docs, but it does not clearly separate architecture layers, story-local allowed/forbidden paths, anti-hallucination rules, or pipeline dependency hints.
- Active story bundles already contain explicit file-scope data in `02_file_scope.md`, but the runner does not reuse that information inside the runtime repository map.
- Tests already cover baseline repository-map generation/injection behavior and should be extended rather than replaced.

## Target Outcome
Each Codex run must produce a stronger `repository_map_runtime.md` that includes:
- architecture layer boundaries
- story-local context derived from the active story bundle
- anti-hallucination rules for Codex
- dependency hints describing how pipeline artifacts relate to each other

The result must stay deterministic, lightweight, and runner-owned.

=== FILE: 01_context_bundle.md ===
# US-AUTO-17: Context Bundle

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/40_ai/zumbot_codex/REPOSITORY_MAP.md`
- `docs/40_ai/zumbot_codex/PROJECT_CONTEXT.md`
- `automation/run_codex_task.sh`
- `tests/test_run_codex_task.py`

## Current Code Reality
- The runner already generates a runtime repository map artifact.
- The current implementation is intentionally lightweight and deterministic, based on curated docs plus top-level repository directories.
- The runner already knows the active `STORY_ID` and bundle directory, so story-local repository-map enrichment can be added without changing the overall run model.
- Story bundles already encode allowed-file scope, which can be surfaced to Codex as architecture context without changing enforcement logic.

## Architectural Intent
- Keep `automation/run_codex_task.sh` as the single owner of repository-map runtime generation.
- Enrich the map with higher-signal architecture guidance instead of building a complex repository crawler.
- Reuse bundle scope as context, not as a second enforcement mechanism.
- Make Codex more architecture-aware before implementation starts, while preserving deterministic runner artifacts.

## Risks
- Overbuilding the repository-map artifact into a mini-framework instead of a compact runtime aid.
- Duplicating allowed-files enforcement logic instead of only surfacing story-local context.
- Making parsing of `02_file_scope.md` brittle if the implementation depends on overly narrow formatting assumptions.
- Mixing future console-UX/chaining concerns into this story.

## Acceptance Notes
- `repository_map_runtime.md` must become visibly richer than the baseline version.
- Layer boundaries must be explicit and repository-valid.
- Story-local context must reflect the active story bundle.
- Anti-hallucination rules must be clearly visible to Codex.
- Dependency hints must describe the runner/review/classification/gate relationship without changing gate logic.

=== FILE: 02_file_scope.md ===
# US-AUTO-17: File Scope

## Files Allowed To Change
- `automation/run_codex_task.sh`
- `tests/test_run_codex_task.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `automation/bundle_packs/US-AUTO-17.bundle.md`
- `automation/bundles/active/US-AUTO-17/**`

## Files Not Allowed To Change
- `automation/scripts/check_allowed_files.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/finalize_story.sh`
- `backend/**`
- `migrations/**`
- `.github/workflows/**`

## Scope Notes
- Keep this story strictly about Repository Map Injection v2.
- Do not introduce new pipeline stages.
- Do not alter allowed-files guard behavior.
- Do not add console UX, chaining, or blocker/warn semantics here.
- Reuse existing curated docs and bundle scope instead of inventing a new metadata system.

=== FILE: 03_master_prompt.md ===
# US-AUTO-17 PROMPT 1 — Repository Map Injection v2

## Role
You are the Zumbot workflow automation engineer working under the repository's CODEX Operating System.

## Goal
Upgrade runtime repository-map injection so Codex receives stronger anti-hallucination architecture context before implementation starts.

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/40_ai/zumbot_codex/REPOSITORY_MAP.md`
- `docs/40_ai/zumbot_codex/PROJECT_CONTEXT.md`
- `automation/run_codex_task.sh`
- `tests/test_run_codex_task.py`

## Files Allowed To Change
- `automation/run_codex_task.sh`
- `tests/test_run_codex_task.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`

## Files Not Allowed To Change
- `automation/scripts/check_allowed_files.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `backend/**`
- `migrations/**`
- `.github/workflows/**`

## Output
1. changed files summary
2. design rationale
3. validation performed
4. risks / follow-ups
5. final diff

## Implementation Requirements
1. Extend `generate_repository_map_runtime()` so the runtime artifact includes an explicit `Architecture Layers` section.
2. Add a `Story-Local Context` section derived from the active story bundle when one exists. At minimum surface:
   - story id
   - active bundle path
   - files allowed to change
   - files not allowed to change (if present and parseable)
3. Add an `Anti-Hallucination Rules` section with compact rules such as:
   - do not invent files
   - do not broaden scope
   - edit only allowed files for this story
   - if source-of-truth docs conflict, stop and report before broad changes
4. Add a `Pipeline Dependency Hints` section that explains the artifact relationships for the automation flow.
5. Keep generation deterministic and lightweight. Do not add non-deterministic scanning or heavyweight repository analysis.
6. Preserve existing manifest metadata and existing prompt/story-context references to the repository-map artifact.
7. Update focused tests to verify the new injected sections.
8. Update `docs/90_codex/STORY_EXECUTION_CHECKLIST.md` so the stronger repository map is part of the expected run artifact.

## Testing
- `pytest tests/test_run_codex_task.py`

## Documentation
- Update only the docs required by the story scope.

=== FILE: 04_review_checklist.md ===
# US-AUTO-17: Review Checklist

## Scope Validation
- [ ] Changes stay inside `02_file_scope.md`
- [ ] No console UX / chaining / resume logic was added
- [ ] No allowed-files enforcement logic was changed
- [ ] No AI review gate behavior was changed
- [ ] No unrelated runner refactor was introduced

## Functional Validation
- [ ] `repository_map_runtime.md` includes architecture layer boundaries
- [ ] `repository_map_runtime.md` includes story-local context for the active story
- [ ] `repository_map_runtime.md` includes anti-hallucination rules
- [ ] `repository_map_runtime.md` includes pipeline dependency hints
- [ ] `story_context.md` still references the repository map artifact
- [ ] `manifest.md` still records repository map injection metadata

## Verification
- [ ] Focused tests updated
- [ ] Manual run command documented
- [ ] Follow-ups for console UX / chaining are deferred to later stories
- [ ] Risks are captured before merge

=== FILE: 05_followups.md ===
# US-AUTO-17: Follow-Ups

## Follow-Up Prompt Queue
- `US-AUTO-18` — Pipeline Console UX Standard
- `US-AUTO-19` — Failure Surfacing & Artifact Summaries
- `US-AUTO-20` — Workflow Chaining & Resume
- `US-AUTO-21` — Long-Running Step Logging
- `US-AUTO-22` — Review Result Rendering

## Iteration Notes
- Keep `US-AUTO-17` narrow: this story improves Codex context quality, not operator-facing UX.
- If parsing `02_file_scope.md` becomes brittle, prefer a compact tolerant parser over a large bundle metadata redesign.
- If additional “hot files” are useful, add them only when they can be derived deterministically from current bundle data.

=== FILE: 06_manual_actions.md ===
# US-AUTO-17: Manual Actions

## Required Human Actions
- Materialize the bundle pack into `automation/bundles/active/US-AUTO-17/`
- Run the story on a feature branch, not on `main`
- Review generated run artifacts, especially:
  - `repository_map_runtime.md`
  - `story_context.md`
  - `manifest.md`
- Confirm the new runtime map is clearer and more useful than the baseline version

## Execution Notes
- Run locally:
  - `automation/scripts/materialize_story_bundle.sh US-AUTO-17`
  - `automation/scripts/validate_story_bundle.sh US-AUTO-17`
  - `automation/scripts/run_story.sh US-AUTO-17`
- Focus manual review on whether story-local context and architecture boundaries are both present and compact.
- Defer operator-facing UX improvements to follow-up stories rather than extending this story.

## Completion Status
- [ ] Manual verification completed
- [ ] Ready for PR