# US-AUTO-23: Context Bundle

## Source of Truth
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`

## Architectural Intent
This story introduces only a durable evidence primitive for story lifecycle history.

The ledger must be:
- append-only
- repository-visible
- human-reviewable
- small enough for downstream machine parsing
- non-blocking by itself

This story records history only. It must not interpret history into stop/continue policy.

## Current Code Reality
- Existing workflow phases already include story start, review/gate, and finalize/close.
- Existing run/review artifacts are useful but fragmented.
- There is not yet one normalized committed artifact that answers how many attempts a story had, what outcomes occurred, and whether the same reject/follow-up pattern repeated.
- Downstream anti-cycle stories are planned, but would currently need to infer history indirectly.

## Implementation Notes
Prefer one lightweight ledger artifact stored under `automation/` and one small append helper.

Prefer a deliberately small normalized entry shape, such as:
- `story_id`
- `timestamp`
- `run_id` or attempt reference
- `branch`
- `pr_number` when known
- `event_type`
- `status` or classification when known
- `reason_code` when known
- `artifact_ref`
- `short_note`

Field names may vary for implementation simplicity, but the schema should remain compact and stable.

Prefer a narrow stable event vocabulary:
- `story_started`
- `review_outcome`
- `story_rejected`
- `story_finalized`

Prefer exactly three integration areas:
1. start path
2. review outcome path
3. finalize/close path

## Risks
- Overdesigning the ledger into a policy engine.
- Recording too many unstable intermediate states.
- Touching too many lifecycle scripts and causing scope drift.
- Mixing evidence collection with enforcement logic.
- Making the schema too heavy for human review.

## Acceptance Notes
Reviewers should confirm that:
- the ledger is clearly evidence-only
- no blocking or scoring behavior was added
- lifecycle integration points remain minimal
- missing optional metadata does not break append behavior
- follow-up capture is used for any enforcement idea discovered during implementation
