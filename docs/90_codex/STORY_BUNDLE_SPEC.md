# STORY BUNDLE SPEC

## Purpose
Define the single-source bundle pack format and the required materialized bundle structure for every story.

## Source of Truth
- Canonical bundle source: `automation/bundle_packs/<STORY-ID>.bundle.md`
- Materialized runtime bundle: `automation/bundles/active/<STORY-ID>/`
- Epic-level lifecycle registry: `docs/90_codex/epics/<EPIC-ID>_REGISTRY.md`
- Bootstrap helper: `automation/scripts/new_story_bundle.sh` (pack scaffold only)

The boundary is intentional:
- Epic registry = epic-level source of truth for story lifecycle, status, and cross-story relationships.
- Bundle pack / active bundle = story-level execution artifact for one story only.
- Story follow-ups in `05_followups.md` queue future work locally, but they do not replace epic-level registry tracking.
- Every story should be traceable from the epic registry to a concrete story artifact or an explicit planning note.

## Bundle Pack Format
Pack files must be deterministic markdown with:

1. Metadata header including `Story-ID: <STORY-ID>`
2. Exactly seven file sections with delimiter lines:
   `=== FILE: <filename> ===`
3. Only these filenames:
   - `00_story.md`
   - `01_context_bundle.md`
   - `02_file_scope.md`
   - `03_master_prompt.md`
   - `04_review_checklist.md`
   - `05_followups.md`
   - `06_manual_actions.md`

Pack files are expanded by `automation/scripts/materialize_story_bundle.sh`.
Materialization must parse + validate before replacing the active bundle directory.

## Required Sections
Every story bundle must include all sections below:

1. Story ID and title
2. Objective
3. Scope
4. Non-goals
5. Dependencies
6. Source of truth
7. Current code reality
8. Target outcome
9. Atomic Task Isolation contract
10. Allowed files
11. Forbidden files
12. Risks
13. Manual actions
14. Acceptance notes

The Atomic Task Isolation contract section must state:
- the single purpose of the story
- the exact intent statement
- explicit out-of-scope items
- the allowed file boundary
- the forbidden file/area boundary
- the hard-stop condition for scope breakage
- how out-of-scope findings become follow-up work instead of inline changes
- that each follow-up prompt isolates exactly one review finding or one narrowly defined blocker

`03_master_prompt.md` and follow-up prompt entries in `05_followups.md` must each include:
- explicit intent line
- explicit out-of-scope line
- allowed and forbidden file boundaries
- explicit statement that Atomic Task Isolation is a mandatory contract for this run
- explicit statement that Codex must declare the one-sentence task intent before making changes
- hard-stop condition
- execution-gate language that requires Codex to stop when the prompt is non-atomic, underspecified, or split across multiple findings
- follow-up capture instruction for newly discovered out-of-scope findings
- explicit statement that follow-up prompts are not an exception path around Atomic Task Isolation

Each follow-up entry in `05_followups.md` must identify exactly one target finding/blocker label from review artifacts and must not combine multiple independent findings in one prompt.
Bundles are invalid for execution when master or follow-up prompts omit this execution-gate language or otherwise leave Atomic Task Isolation ambiguous.

## Bundle File Layout (Recommended)
- `00_story.md`: story identity, objective, scope, non-goals, dependencies, Atomic Task Isolation contract.
- `01_context_bundle.md`: source-of-truth docs, current reality, architectural intent, risks.
- `02_file_scope.md`: allowed and forbidden file list with explicit scope notes.
- `03_master_prompt.md`: executable implementation prompt draft with explicit Atomic Task Isolation instructions for the current run.
- `04_review_checklist.md`: verification and review criteria, including scope-drift checks and follow-up decomposition checks.
- `05_followups.md`: follow-up prompts and iteration notes for out-of-scope findings and later improvements; each follow-up entry must remain atomic, independently reviewable, and limited to one finding or blocker. Epic registries must capture any resulting new story IDs and lifecycle state at the epic level.
- `06_manual_actions.md`: out-of-band actions required by humans/systems.

## Validation Rules
`automation/scripts/validate_story_bundle.sh` must reject bundles when any of the following are true:

- missing required files
- empty files
- unresolved canonical placeholder token remains
- required core sections are missing

`automation/scripts/run_story.sh` must invoke validation before execution and refuse invalid bundles.

## Quality Requirements
- Keep sections explicit and short.
- Mark legacy behavior vs target architecture when both exist.
- Separate implementation scope from future stories.
- Keep file paths concrete and repository-valid.
- Make the Atomic Task Isolation contract explicit enough that Codex can identify what is in scope, what is forbidden, and when it must stop.
- Require Codex to restate the one-sentence intent before edits so reviewers can verify the run stayed atomic.
- Treat missing Atomic Task Isolation prompt fields as a bundle defect that blocks execution until corrected.
- Record newly discovered out-of-scope work in follow-up sections instead of folding it into the current story.
- When a follow-up becomes a real story ID, add or update the corresponding epic registry entry so story-local planning is reflected at epic level.
- Do not use follow-up sections to batch unrelated cleanup; each follow-up must isolate a single narrowly scoped task.
- When review produces multiple findings, split them into separate follow-up prompts instead of composing a multi-fix continuation.
- Follow-up templates must say explicitly that follow-up execution is still bound by the same one-purpose contract and cannot absorb a second independently reviewable fix.
- For automation workflow stories, prefer deterministic stage models and exact next-command output that can safely resume from existing artifacts without hidden state.
- For automation workflow stories, document the canonical resumable stage sequence explicitly and treat reject/invalid/stale/dirty conditions as blocked states rather than implicit stages.
- For automation workflow stories, reserve `latest valid stage` for canonical resumable checkpoints only; blocked conditions should report the last valid checkpoint separately instead of becoming new resumable stages.
- For automation workflow stories, next-command output should pin `AUTOMATION_RUN_DIR` to one concrete run directory and downstream resume scripts should accept both absolute and repository-relative pinned run paths.
- For automation workflow stories that rely on review artifacts, gate enforcement should recompute the authoritative git delta from immutable manifest metadata (`review_artifact_base` with current `HEAD`) and reject fail-closed when `changed_files.txt` or `diff.patch` diverges from that regenerated reality.
- For automation workflow stories that write lifecycle history, keep ledger writes append-only and evidence-only; do not use ledger entries as run-blocking policy in the same story.
- For automation workflow stories that add repository-visible lifecycle evidence, document the canonical ledger artifact path explicitly and whether that path is durable or ephemeral so downstream stories do not treat ephemeral workflow side effects as implementation drift.
- For automation workflow stories that mark a ledger path as ephemeral, the same explicit path contract must be reused for dirty-tree checks, diff generation, and exit cleanup in run/review/finalize scripts so real implementation drift remains strictly visible.
- Bundle must be usable by both humans and Codex without additional interpretation.
