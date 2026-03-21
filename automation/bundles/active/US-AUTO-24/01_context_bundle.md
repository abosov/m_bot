# US-AUTO-24: Context Bundle

## Source of Truth
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/US-AUTO-23.bundle.md`
- `automation/bundles/active/US-AUTO-23/00_story.md`
- `automation/bundles/active/US-AUTO-23/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-23/04_review_checklist.md`

## Current Code Reality
- The current ledger workflow contract is internally inconsistent.
- The workflow currently tries to satisfy all of the following at once:
  - a clean working tree before run and review
  - review artifacts that match the code under review
  - durable committed ledger evidence
  - a terminal `story_finalized` event persisted in shared history
- The current sequencing cannot satisfy all four simultaneously because terminal evidence is appended after merge/cleanup, while other durable evidence expectations and review artifacts are bound to the feature-branch review snapshot.
- Downstream anti-cycle stories cannot safely treat the current ledger as canonical workflow evidence until the contract is redesigned.

## Architectural Intent
- Keep the ledger evidence-oriented, not a policy engine.
- Make durable evidence explainable directly in shared git history.
- Ensure review always evaluates the exact snapshot proposed for merge.
- Preserve clean-tree hygiene while allowing only tightly scoped workflow-produced ledger writes.
- Make event timing simple enough for operators and later runtime implementation stories to follow consistently.

## Problem Statement
The durable ledger workflow introduced by `US-AUTO-23` is useful as an evidence primitive, but its current sequencing creates a contradiction between terminal evidence, clean-tree enforcement, and review artifact freshness.

## Confirmed Blockers
1. `story_finalized` is appended after merge/cleanup, so the final event is not durable in the same shared reviewed history as the rest of the story evidence.
2. `automation/run_codex_task.sh` ignores ledger dirtiness too broadly, weakening the clean-tree boundary.
3. Review artifacts become stale whenever a post-run or post-review ledger commit is required.
4. Anti-cycle enforcement work must remain blocked until the ledger contract is redesigned.

## Decision Options

### Option A — Feature-branch durability before review
- Write all review-relevant events on the feature branch.
- Commit them before generating or consuming downstream review aifacts.
- Treat `story_finalized` as the terminal event for the branch snapshot that is actually reviewed.
- Pros: review and durable history stay aligned; downstream automation sees one canonical branch history.
- Cons: finalization timing must move earlier than the current post-merge cleanup script.

### Option B — Post-merge durability on `main`
- Treat ledger durability as a merge-state concern only.
- Allow review artifacts to omit terminal evidence and write `story_finalized` after merge.
- Pros: no pre-merge terminal event redesign needed.
- Cons: durable evidence no longer matches the reviewed feature-branch snapshot; downstream feature-branch consumers cannot rely on it.

### Option C — Dedicated follow-up commit after review
- Review the feature branch, then require a ledger-only commit before merge or immediately after review approval.
- Pros: preserves a commit for ledger evidence.
- Cons: review artifacts become stale unless review reruns; creates an avoidable extra staransition.

### Option D — Externalized durable sink
- Store terminal evidence outside the feature branch in a separate durable system.
- Pros: avoids git-timing conflicts.
- Cons: violates the current evidence-in-repository workflow and broadens the architecture significantly.

## Chosen Recommendation
Choose **Option A — Feature-branch durability before review**.

This is the only option that satisfies all core workflow goals without introducing stale review artifacts or redefining durability away from shared git history.

## Canonical Event Model

| Event | Producer | Timing | Commit required before downstream consumption? | Workflow state | Contract notes |
|---|---|---|---|---|---|
| `story_started` | Story run launcher for the active story | Immediately after clean-tree preflight passes and the story run is officially started | Yes | Feature-branch state | This is the first durable evidence that a new attempt exists. It must land on the feature branch before later review or anti-cylogic treats the attempt as canonical history. |
| `review_outcome` | Review gate / review classification step | Immediately after the review result for the current branch snapshot is finalized | Yes | Review state | The review artifact and the ledger write must describe the same reviewed commit range. If the review outcome changes, the review step must regenerate both together. |
| `story_rejected` | Review gate when the review outcome requires follow-up instead of merge | Written in the same review step that produces the rejecting `review_outcome` | Yes | Review state | This event is not a later operator annotation; it is the durable branch-local evidence that the reviewed snapshot was rejected and needs another attempt. |
| `story_finalized` | Finalization step for an approved feature-branch snapshot | After the branch is review-complete and ready for merge, but before merge/cleanup occurs | Yes | Feature-branch state | Terminal evidence must exist in the same reviewed feature-branch history as the rest of the story ledger. Merge/cleanup may still happen later, but they are operational steps rather than the source of durable terminal evidence. |

## Durability Contract
“Durable evidence” means:
- the ledger event is written to the repository ledger,
- the event is committed on the shared feature branch,
- the commit containing that event is the same snapshot consumed by the next workflow stage, and
- downstream scripts or operators do not rely on the event until that commit exists.

This story rejects post-merge-only durability and rejects ledger-only commits inserted after review artifacts are generated.

## Review Artifact Consistency Contract
Review artifacts remain valid only when all of the following are true:
1. the branch is clean before the review step begins,
2. any review-generated ledger event for that step is written during the same review operation,
3. the ledger write is committed before the review artifact is treated as final downstream evidence, and
4. no extra commitinserted between the reviewed snapshot and the merge candidate.

Operationally, this means a review bundle must correspond to the exact commit range that already contains the relevant `review_outcome`, `story_rejected`, or approved-path `story_finalized` evidence for that review cycle.

## Clean-Tree Boundary Contract
- Before a run or review step begins, the working tree must be clean, including the ledger file.
- The only acceptable ledger mutation during a workflow step is the exact append generated by that step for the active story.
- That mutation must be committed before the next downstream consumer uses it.
- Pre-existing local ledger edits, manually edited ledger lines, or unrelated story ledger dirtiness remain hygiene failures.
- A future implementation may narrow hygiene exceptions to the expected ledger file plus the expected event emitted by the active workflow step, but it must not treat arbitrary ledger dirtiness as acceptable.

## Finalization Semantics
`story_finalized` is redefined as **terminal feature-branch evidence**, not as a post-merge cleanup artifact.

That means:
- the reviewed branch snapshot receives the terminal event before merge,
- the final review artifact and the final ledger state stay aligned,
- merge to `main` becomes an operational publication step rather than the moment durability first exists, and
- cleanup after merge may still occur, but it must not be the only place that writes terminal evidence.

## Operator Workflow
1. Start from a clean feature branch.
2. Run the story so `story_started` is written and committed as the first durable attempt marker.
3. Produce the candidate code changes.
4. Run review so the review artifact and any review-ledger events are produced from the same branch snapshot.
5. If review rejects the story, commit `review_outcome` and `story_rejected` together before beginning another attempt.
6. If review approves and the branch is ready to merge, write and commit `story_finalized` on the feature branch before merge.
7. Merge the already-reviewed and already-finalized branch.
8. Perform cleanup as a separate operational phase that does not create the first durable copy of terminal evidence.

## Risks
- Moving `story_finalized` into feature-branch state requires a later runtime story to separate terminal evidence from post-merge cleanup side effects.
- If a future implementation allows broad ledger dirtiness exceptions, it would reintroduce the current hygiene flaw.
- If operators skip the commit boundaries defined here, anti-cycle logic would again consume stale or non-durable evidence.

## Acceptance Notes
- The bundle must explicitly define producer, timing, commit requirement, and workflow state for each canonical event.
- The recommendation must define durable evidence in terms of shared committed history.
- Review artifact validity must depend on matching the exact reviewed snapshot.
- Finalization semantics must be resolved without relying on a post-merge-only terminal append.
- The story must remain design-only and defer all runtime changes to follow-up work.
