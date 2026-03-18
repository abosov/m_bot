# Story Bundle Pack
Story-ID: US-AUTO-22
Version: 1

This pack is the single source of truth for materialized story bundle files.

=== FILE: 00_story.md ===
# US-AUTO-22: Atomic Task Isolation Rule for Codex Workflow

## Story ID and Title
- Story ID: `US-AUTO-22`
- Title: `Atomic Task Isolation Rule for Codex Workflow`

## Objective
Introduce a strict Atomic Task Isolation rule into the Codex workflow so each story stays single-purpose, explicitly scoped, minimally patched, and unable to silently absorb adjacent fixes.

## Scope
- Update Codex workflow documentation to define the Atomic Task Isolation rule.
- Update prompt/template materials so Codex must declare intent, allowed files, forbidden areas, and follow-up handling for out-of-scope findings.
- Keep this story documentation/prompt-template only unless a later separate story adds enforcement in scripts.

## Non-goals
- Do not change `automation/run_codex_task.sh`.
- Do not change allowed-files guard behavior.
- Do not change review gate behavior.
- Do not add merge/finalization automation.
- Do not implement automatic enforcement in shell scripts in this story.

## Dependencies
- Existing story bundle workflow.
- Existing Codex prompt templates.
- Existing bundle spec and execution checklist.

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/40_ai/zumbot_codex/MASTER_PROMPT_TEMPLATE.md`
- `docs/40_ai/zumbot_codex/FOLLOWUP_PROMPT_TEMPLATE.md`

## Current Code Reality
- The master prompt already includes minimal-patch and allowed-files discipline, but did not yet define a complete Atomic Task Isolation rule with explicit stop conditions and mandatory follow-up handling.
- The follow-up prompt already discouraged scope expansion and unrelated refactoring, but did not yet formalize decomposition and isolation as a documented workflow contract.

## Target Outcome
- Codex workflow docs explicitly define Atomic Task Isolation as a first-class rule.
- Prompt templates require exact task intent, exact allowed files, no scope expansion, and follow-up capture instead of drive-by fixes.
- This story remains documentation/template-only and defers script enforcement to a separate follow-up story.

## Atomic Task Isolation Contract

### Allowed Scope
- Only documentation and prompt template updates related to Codex workflow.

### Forbidden Scope
- No changes to automation scripts.
- No changes to runtime behavior.
- No changes to test infrastructure.

### Intent (one sentence)
Introduce a strict Atomic Task Isolation rule into Codex prompts and workflow documentation.

### Out of Scope
- Enforcement in shell scripts (separate story).
- Any refactoring of existing automation.

=== FILE: 01_context_bundle.md ===
# US-AUTO-22: Context Bundle

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/40_ai/zumbot_codex/MASTER_PROMPT_TEMPLATE.md`
- `docs/40_ai/zumbot_codex/FOLLOWUP_PROMPT_TEMPLATE.md`

## Current Code Reality
- The Codex workflow already contains some scope-control language, but the contract is fragmented between templates and not stated as a single mandatory Atomic Task Isolation rule.
- Story bundle workflow already expects explicit scope and source-of-truth discipline, so this change should strengthen existing behavior rather than introduce a new process family.

## Architectural Intent
- Make Atomic Task Isolation an explicit workflow contract across story prompts and follow-up prompts.
- Keep the implementation documentation-only in this story.
- Defer any shell enforcement or runtime automation to a separate future story.

## Risks
- If wording is too vague, Codex may continue to broaden scope despite the new rule.
- If this story drifts into automation-script changes, it will violate its own isolation contract.

## Acceptance Notes
- Bundle content must be fully resolved with no canonical placeholder tokens.
- Materialized files must clearly express allowed scope, forbidden scope, and hard stop conditions.
- The resulting story must remain documentation/prompt-template only.

=== FILE: 02_file_scope.md ===
# US-AUTO-22: File Scope

## Files Allowed To Change
- `automation/bundle_packs/US-AUTO-22.bundle.md`
- `automation/bundles/active/US-AUTO-22/00_story.md`
- `automation/bundles/active/US-AUTO-22/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-22/02_file_scope.md`
- `automation/bundles/active/US-AUTO-22/03_master_prompt.md`
- `automation/bundles/active/US-AUTO-22/04_review_checklist.md`
- `automation/bundles/active/US-AUTO-22/05_followups.md`
- `automation/bundles/active/US-AUTO-22/06_manual_actions.md`
- `docs/40_ai/zumbot_codex/MASTER_PROMPT_TEMPLATE.md`
- `docs/40_ai/zumbot_codex/FOLLOWUP_PROMPT_TEMPLATE.md`
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`

## Files Not Allowed To Change
- `automation/scripts/**`
- `automation/run_codex_task.sh`
- `automation/scripts/check_allowed_files.sh`
- `automation/scripts/review_gate_story_run.sh`
- `tests/**`
- `backend/**`

## Scope Notes
- This exact allowlist matches the reviewed US-AUTO-22 changed-file set: the bundle pack, all seven materialized active-bundle files, and the five Codex docs/template files updated by the story.
- Do not change runtime automation, enforcement scripts, or tests in this story.
- If script enforcement is needed, create a separate follow-up story.

=== FILE: 03_master_prompt.md ===
# US-AUTO-22 PROMPT 1 — Atomic task isolation rule for Codex workflow

## Role
You are the System Architect + Data Architect + UX + Developer + Tech Writer + QA + Security Reviewer for Zumbot.

## Task
Update Codex workflow documentation and prompt templates so Atomic Task Isolation becomes an explicit mandatory contract for story execution and follow-up execution.

## Mandatory Context
Read and follow:
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/40_ai/zumbot_codex/MASTER_PROMPT_TEMPLATE.md`
- `docs/40_ai/zumbot_codex/FOLLOWUP_PROMPT_TEMPLATE.md`
- `automation/bundles/active/US-AUTO-22/00_story.md`
- `automation/bundles/active/US-AUTO-22/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-22/02_file_scope.md`

## Goal
Make Atomic Task Isolation explicit in the source-of-truth docs, prompt templates, and US-AUTO-22 bundle artifacts without changing runtime scripts or test infrastructure.

## Non-goals
Do not:
- modify any automation shell scripts
- change allowed-files guard behavior
- change review gate behavior
- add runtime enforcement
- refactor unrelated documentation

## Source of Truth
- `automation/bundles/active/US-AUTO-22/00_story.md`
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`

## Files Allowed To Change
- `automation/bundle_packs/US-AUTO-22.bundle.md`
- `automation/bundles/active/US-AUTO-22/00_story.md`
- `automation/bundles/active/US-AUTO-22/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-22/02_file_scope.md`
- `automation/bundles/active/US-AUTO-22/03_master_prompt.md`
- `automation/bundles/active/US-AUTO-22/04_review_checklist.md`
- `automation/bundles/active/US-AUTO-22/05_followups.md`
- `automation/bundles/active/US-AUTO-22/06_manual_actions.md`
- `docs/40_ai/zumbot_codex/MASTER_PROMPT_TEMPLATE.md`
- `docs/40_ai/zumbot_codex/FOLLOWUP_PROMPT_TEMPLATE.md`
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`

## Files Not Allowed To Change
- `automation/scripts/**`
- `automation/run_codex_task.sh`
- `tests/**`
- `backend/**`

## Implementation Rules
- minimal patch only
- no unrelated refactor
- no formatting-only edits
- update docs only when behavior/process changes require it
- keep this story documentation/prompt-template only
- keep the allowlist aligned to the reviewed story changed-file set; do not under-declare bundle files that this story legitimately updates
- if shell enforcement is needed, record it as a follow-up story instead of implementing it here

## Test Plan
- Validate that the story bundle materializes without unresolved placeholders.
- Review changed documentation for explicit Atomic Task Isolation language.
- No pytest changes required for this documentation-only story.

## Output
Return:
1. changed files summary
2. rationale
3. validation results
4. risks/follow-ups
5. final diff

=== FILE: 04_review_checklist.md ===
# US-AUTO-22: Review Checklist

## Scope Validation
- [ ] Changes stay inside the exact reviewed changed-file set declared in `02_file_scope.md`
- [ ] `03_master_prompt.md` and `02_file_scope.md` declare the same allowed implementation surface
- [ ] Source-of-truth files are complete and resolved
- [ ] No unrelated refactor or formatting-only edits

## Functional Validation
- [ ] Bundle materializes into all seven required files
- [ ] Validation blocks unresolved placeholders and incomplete structure
- [ ] Story remains documentation/prompt-template only

## Architecture / Source of Truth
- [ ] Source-of-truth docs are listed and followed
- [ ] Architecture boundaries remain intact
- [ ] Atomic Task Isolation is expressed consistently across docs and templates

## Verification
- [ ] Validation commands are recorded
- [ ] Manual verification steps are recorded when needed
- [ ] Risks and follow-ups are captured before merge

## Review Prompt Seed


# US-AUTO-22 REVIEW PROMPT — Implementation Review

## Role
You are the Reviewer (Architect + QA + Security) for Zumbot.

## Review Inputs
- Story bundle: `automation/bundles/active/US-AUTO-22/`
- Code diff: `<git diff against branch>`
- Test evidence: `bundle validation and manual doc review`
- Classification rules: `docs/90_codex/REVIEW_CLASSIFICATION_RULES.md`

## Review Task
1. Validate scope against allowed/forbidden files.
2. Validate architecture and source-of-truth compliance.
3. Validate the story remains documentation-only.
4. Classify each finding:
   - `MERGE BLOCKER`
   - `MINOR IMPROVEMENT`
   - `FOLLOW-UP STORY`

## Output
Return:
1. Findings by severity/classification
2. Required fixes before merge
3. Optional improvements
4. Follow-up stories to create
5. Merge recommendation (`approve` or `reject`)

Include the final recommendation as an exact standalone line:
`MERGE RECOMMENDATION: approve`
or
`MERGE RECOMMENDATION: reject`

=== FILE: 05_followups.md ===

# US-AUTO-22: Follow-Ups
## Follow-Up Prompt Queue

Add a separate follow-up story for shell/script-level enforcement of Atomic Task Isolation if documentation alone proves insufficient.

## Iteration Notes

This story intentionally stops at documentation and prompt-template updates.

Any runtime enforcement, gate changes, or allowed-files guard changes require a separate story.

## Follow-Up Prompt Template

# US-AUTO-22 FOLLOW-UP PROMPT 1 — <Fix/Adjustment>

## Role
You are the System Architect + Developer + QA + Security Reviewer for Zumbot.

## Context
- Base story bundle: `automation/bundles/active/US-AUTO-22/`
- Previous run output: `automation/output/<story-run-id>/`
- Review checklist: `automation/bundles/active/US-AUTO-22/04_review_checklist.md`

## Target
Address only the specific documented finding from the previous run without expanding scope.

## Findings To Address
- <paste exact finding>

## Files Allowed To Change
- <list exact allowed files for the follow-up>

## Files Not Allowed To Change
- `automation/scripts/**`
- `tests/**`
- any files unrelated to the listed finding

## Rules
- keep patch minimal and scoped
- preserve architecture boundaries
- do not introduce new features beyond listed findings
- if another issue is discovered, record it as a new follow-up instead of fixing it here

## Tests
- Record validation performed for the addressed finding.

## Output
Return:
1. addressed findings
2. changed files summary
3. validation results
4. residual risks
5. final diff

=== FILE: 06_manual_actions.md ===

# US-AUTO-22: Manual Actions

## Required Human Actions

- Fill in final PR metadata fields after implementation and review.
- Run bundle materialization and validation locally before starting Codex execution.

## Execution Notes

- This story should not proceed into implementation until the active bundle is fully materialized and validated.
- If implementation pressure pushes toward script enforcement, stop and create a separate story instead.

## Completion Status

-  No manual actions required
-  Manual actions completed and documented
