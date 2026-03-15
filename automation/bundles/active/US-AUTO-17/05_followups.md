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

