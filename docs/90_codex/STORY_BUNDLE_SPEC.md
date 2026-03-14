# STORY BUNDLE SPEC

## Purpose
Define the single-source bundle pack format and the required materialized bundle structure for every story.

## Source of Truth
- Canonical bundle source: `automation/bundle_packs/<STORY-ID>.bundle.md`
- Materialized runtime bundle: `automation/bundles/active/<STORY-ID>/`
- Bootstrap helper: `automation/scripts/new_story_bundle.sh` (pack scaffold only)

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
9. Allowed files
10. Forbidden files
11. Risks
12. Manual actions
13. Acceptance notes

## Bundle File Layout (Recommended)
- `00_story.md`: story identity, objective, scope, non-goals, dependencies.
- `01_context_bundle.md`: source-of-truth docs, current reality, architectural intent, risks.
- `02_file_scope.md`: allowed and forbidden file list.
- `03_master_prompt.md`: executable implementation prompt draft.
- `04_review_checklist.md`: verification and review criteria.
- `05_followups.md`: follow-up prompts and iteration notes.
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
- Bundle must be usable by both humans and Codex without additional interpretation.
