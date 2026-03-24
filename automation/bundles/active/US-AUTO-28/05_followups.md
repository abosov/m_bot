# Follow-ups

## Follow-Up Prompt Queue
1. **US-AUTO-25 — loop detection**
   - richer repeated-reject detection across categories / history
   - generalized loop telemetry and stronger classification of loop patterns

2. **US-AUTO-26 — protection from repeated identical runs**
   - block run when HEAD/diff is unchanged before expensive repeated execution
   - broader deduplication before run

3. **US-AUTO-27 — tighter pipeline zone boundaries**
   - refine where each stage may write and how scope is enforced across stages

## Iteration Notes
- Keep US-AUTO-28 intentionally small and deterministic.
- If implementation requires broader history indexing, heavy diff comparison, or cross-story analytics, stop and capture a follow-up instead of widening this story.
- Prefer explicit escalation metadata over hidden log-only behavior.

