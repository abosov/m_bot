
## Source of Truth

run_story.sh
run_codex_task.sh

## Current Code Reality

Codex produces superset diffs.
Pipeline expects exact-scope diffs.
Mismatch causes systemic failure.

## Architectural Intent

System must be robust to generator noise.

Key rule:

Pipeline trusts scope, not generator.

## Risks

* silent acceptance of invalid changes
* incomplete subset extraction

## Acceptance Notes

Must prove:

* subset extraction works
* invalid files are excluded

---

