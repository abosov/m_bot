# Follow-ups — US-AUTO-40

## Follow-Up Prompt Queue
- US-AUTO-41 — Single source of truth for scope contract
- US-AUTO-37 — Ephemeral automation paths contract
- US-AUTO-38 — Automatic rollback after failed automation run
- US-AUTO-35 — Head-bound run resolution and run-local scope enforcement
- US-AUTO-36 — Preflight hygiene enforcement

## Iteration Notes
US-AUTO-40 should enforce artifact fidelity without trying to redesign the full multi-file scope-authority model.

Implemented in this story:
- fail-closed gate fidelity checks for `diff.patch` and `changed_files.txt` against regenerated diff data from manifest `review_artifact_base`.
- deterministic reject reasons for stale/mismatched fidelity artifacts.

Depending on implementation details, future work may still need to:
- centralize reviewed file-set declaration;
- formalize artifact freshness markers;
- improve remediation UX for fidelity failures;
- classify runtime-managed files more cleanly in later stories.
