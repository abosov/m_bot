# US-AUTO-41: Follow-Ups

## Follow-Up Prompt Queue
- Preview exact pending story artifact paths before commit handoff.
- Detect partially materialized story artifacts before commit handoff.
- Add an explicit operator helper that chains materialize and commit only when intentionally invoked.
- Add broader story lifecycle state introspection as a separate story.
- Revisit adjacent ledger-artifact workflow friction only if it remains visible after this handoff lands.

## Iteration Notes
- Keep `US-AUTO-41` narrow and contract-focused.
- Do not replace the explicit `materialize -> commit -> run` handoff with hidden auto-commit behavior.
- Treat future UX polish as separate follow-up work rather than extending this story.