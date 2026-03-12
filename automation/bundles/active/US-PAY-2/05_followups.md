# US-PAY-2 Follow-up Prompts Register

## Purpose
Track approved follow-up prompts after initial US-PAY-2 implementation run.

## Follow-up Prompt Template
Use `automation/templates/followup_prompt_template.md`.

## Candidate Follow-up Slots
1. `US-PAY-2 FOLLOW-UP PROMPT 1`
   - Trigger: merge blocker in adapter/service logic.
   - Target: minimal fix + tests.
2. `US-PAY-2 FOLLOW-UP PROMPT 2`
   - Trigger: accepted minor improvement.
   - Target: low-risk quality improvement within allowed files.
3. `US-PAY-2 FOLLOW-UP STORY`
   - Trigger: out-of-scope finding (API route wiring, webhook path, UI coupling).
   - Target: create new story bundle (`US-PAY-3`/`US-PAY-4` or separate story ID).

## Recording Format
- Date:
- Prompt ID:
- Finding classification:
- Files changed:
- Tests run:
- Outcome:
