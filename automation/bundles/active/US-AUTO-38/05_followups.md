# US-AUTO-38: Follow-Ups

## Follow-Up Prompt Queue
- Add richer structured rollback diagnostics if current terminal output is insufficient.
- Add preflight classification of failure mode before mutable execution begins.
- Add repeated-failure stop conditions or loop-prevention enforcement if needed.
- Extract shared rollback helper logic only if lifecycle complexity grows enough to justify it.

## Iteration Notes
- Keep this story limited to failed-run automatic rollback.
- Prefer centralized orchestration ownership over distributed cleanup logic.
- Prefer deterministic clean-state restoration over convenience features.
- Do not expand this story into broader workflow redesign.

