
## Source of Truth

* semantic_companion_filter.sh
* run artifact: semantic_projection.json (or equivalent)

## Current Code Reality

* Projection is implicit
* Stages recompute filtering independently

## Architectural Intent

Shift from:

logic-based projection

to:

artifact-based projection

## Risks

* Hidden recomputation paths
* Tests expecting old behavior
* Partial adoption across stages

## Acceptance Notes

Projection must be:

* produced once
* persisted
* immutable
* consumed, not recomputed

---

