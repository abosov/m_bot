# STORY BUNDLE SPEC

## Purpose
Define the minimum required structure for every story bundle in `automation/bundles/active/<STORY-ID>/`.

## Required Sections
Every story bundle must include all sections below:

1. Story ID and title
2. Objective
3. Scope
4. Non-goals
5. Dependencies
6. Source of truth
7. Current code reality
8. Target architecture
9. Allowed files
10. Forbidden files
11. Risks
12. Manual actions
13. Acceptance notes

## Bundle File Layout (Recommended)
- `00_story.md`: story identity, objective, scope, non-goals, dependencies.
- `01_context_bundle.md`: source-of-truth docs, current reality, target architecture, risks.
- `02_file_scope.md`: allowed and forbidden file list.
- `03_master_prompt.md`: executable implementation prompt draft.
- `04_review_checklist.md`: verification and review criteria.
- `05_followups.md`: follow-up prompts and iteration notes.
- `06_manual_actions.md`: out-of-band actions required by humans/systems.

## Quality Requirements
- Keep sections explicit and short.
- Mark legacy behavior vs target architecture when both exist.
- Separate implementation scope from future stories.
- Keep file paths concrete and repository-valid.
- Bundle must be usable by both humans and Codex without additional interpretation.
