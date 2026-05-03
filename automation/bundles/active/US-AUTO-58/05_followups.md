## Follow-Up Prompt Queue

US-AUTO-31:

    Make analyze the mandatory decision authority before rerun, refresh, review continuation, classification, gate, escalation, follow-up, or phase advance.

US-AUTO-79:

    Add story pipeline orchestrator for deterministic stage chaining after US-AUTO-58 and US-AUTO-31 are resolved.

US-AUTO-80:

    Add compact operator/AI decision packet UX for non-deterministic stops, or fold into US-AUTO-79 only if still atomic.

Potential follow-up:

    Add machine-readable loop-state output if US-AUTO-58 only introduces textual markers and US-AUTO-79 needs structured fields.

Potential follow-up:

    Add better review artifact refresh command templates for docs/governance stories, including bundle validation, live HEAD proof, branch proof, and story-scoped pytest/full pytest where required.

## Iteration Notes

US-AUTO-78 showed that loops are broader than Codex rerun loops.

The loop can occur through refresh/review/classify/fix/refresh even when run_story is no longer used.

US-AUTO-58 must therefore treat stage-loop cap as a pipeline-level behavior, not only a run_story behavior.

Classification rejects should be interpreted carefully:

    - explicit safety/source-of-truth blocker: allow narrow fix;
    - non-safety polish/preference: prefer follow-up/escalation;
    - evidence/fidelity churn: force decision rather than repeat the loop.

Future orchestration must not accelerate loops. It must stop earlier with decision packets.

