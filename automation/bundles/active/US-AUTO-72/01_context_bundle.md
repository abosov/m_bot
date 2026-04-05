
## Source of Truth

run_story.sh
run_codex_task.sh

## Current Code Reality

Codex produces superset diffs.
Pipeline expects exact-scope diffs.
Mismatch causes systemic failure.

## Architectural Intent

System must be robust to generator noise without weakening scope enforcement.

Key rules:

* pipeline trusts scope, not generator
* explicit companion contamination may be isolated
* real out-of-scope changes must still block execution
* delivery isolation must not become a generic pre-scope filtering layer

## Risks

* silent acceptance of invalid changes
* incomplete subset extraction

## Acceptance Notes

Must prove:

* explicit companion contamination is isolated correctly
* real out-of-scope changes are still rejected
* no generic filtering of arbitrary changed paths is introduced

---

