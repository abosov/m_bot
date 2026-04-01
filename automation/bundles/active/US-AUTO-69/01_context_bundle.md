## Source of Truth
- `docs/90_codex/epics/US-AUTO_REGISTRY.md` is the durable portfolio source of truth for story priority, status, and dependencies. It lists US-AUTO-69 as the next recommended story and explains that US-AUTO-57 is blocked by a companion-artifact execution defect. :contentReference[oaicite:4]{index=4}
- Runtime behavior must remain aligned with the established fail-closed execution pipeline already documented in the registry’s current epic state and workflow observations. :contentReference[oaicite:5]{index=5}

## Current Code Reality
The registry states that the remaining work after US-AUTO-56 is about cycle-cost reduction and stronger workflow decisions rather than missing fail-closed contracts. US-AUTO-57 attempted rerun-skip detection but became blocked because Codex introduced a companion registry diff that was outside scope, making the success boundary unreachable through `run_story.sh`. US-AUTO-69 exists specifically to fix that execution-layer defect without broadening the story’s allowed scope. :contentReference[oaicite:6]{index=6}

Existing pipeline guarantees already include:
- explicit handoff before run
- preflight dirty-state classification
- committed-HEAD review boundary enforcement
- exclusion of committed active-story bundle artifacts from runtime scope validation
- deterministic review evidence contracts
These guarantees should remain intact. :contentReference[oaicite:7]{index=7}

## Architectural Intent
The correct fix is a narrow execution-layer filter for a recognized class of companion artifacts on code-only stories.
Architectural intent:
- preserve fail-closed behavior
- preserve deterministic review-surface fidelity
- do not silently widen allowed story scope
- keep the distinction between actual implementation delta and companion artifacts
- make the execution flow cheaper and less fragile only where the extra diff is known to be non-implementation noise

The system should treat companion artifacts as excluded from the effective implementation review surface, not as ordinary allowed edits.

## Risks
Primary risks:
- over-classifying companion paths and hiding true scope violations
- under-classifying and leaving US-AUTO-57 blocked
- creating inconsistency between filtered changed-files output and execution diff output
- accidental spread into broader validation, retry, UX, or orchestration work

Mitigation:
- keep path classification explicit and minimal
- add binary tests for companion-only, mixed, and non-companion cases
- keep filtering confined to the execution path and its immediate evidence outputs

## Acceptance Notes
The story is acceptable only if:
- recognized companion paths are filtered deterministically
- non-companion out-of-scope edits still reject
- mixed cases still reject
- the fix is limited to the execution layer for code-only stories
- the bundle scope and implementation scope remain perfectly aligned

