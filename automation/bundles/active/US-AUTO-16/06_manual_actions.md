# US-AUTO-16: Manual Actions

## Required Human Actions
- Confirm the story bundle materializes and validates successfully.
- Review existing review artifacts flow for the latest story run format.

## Implementation
- Implement the AI review gate entrypoint script within the allowed automation scope only.
- Reuse existing AI review and classification scripts instead of duplicating their logic.

## Verification
- Run `automation/scripts/materialize_story_bundle.sh US-AUTO-16`
- Run `automation/scripts/validate_story_bundle.sh US-AUTO-16`
- Run the new review gate script against a story run that already has review artifacts.
- Verify the gate result artifact contains an explicit `approve` or `reject` decision.
- Verify the script exits non-zero when the decision is reject or cannot be derived.

## Completion Status
- Record any follow-up needed for finalize integration as a separate story.
- Keep merge/finalize integration out of this story.
