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
- The source-of-truth Codex workflow docs already define Atomic Task Isolation as a mandatory contract, including explicit stop conditions, mandatory follow-up capture, and one-finding-per-follow-up execution.
- The remaining work in this story is to align the prompt templates and story bundle artifacts so the same mandatory contract is explicit and auditable everywhere this workflow is executed.

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
Introduce Atomic Task Isolation as an explicit mandatory contract in Codex workflow docs and prompt templates for this story.

### Out of Scope
- Enforcement in shell scripts (separate story).
- Any refactoring of existing automation.

### Follow-Up Capture
- If out-of-scope issues are discovered during implementation or review, they must be recorded as explicit follow-up tasks instead of being fixed inside this story.
- Follow-up tasks must include a short title, the concrete problem, and the suggested next action.
- Each follow-up task must isolate exactly one review finding or one narrowly defined blocker.
- Follow-up prompts are not an exception path around this contract; they must satisfy the same atomic boundaries and execution-gate rules as the master prompt and must not absorb a second independently reviewable fix.

### Hard Stop
- If completing this story requires runtime automation changes, shell enforcement, test-infrastructure changes, or unrelated refactoring, stop and open a separate story.
- Do not expand this story beyond documentation, prompt templates, bundle pack updates, and materialized active bundle updates.
- If the required intent, out-of-scope, file-boundary, follow-up-capture, or hard-stop fields are missing or ambiguous in the executable prompt, stop and correct the prompt before implementation.
