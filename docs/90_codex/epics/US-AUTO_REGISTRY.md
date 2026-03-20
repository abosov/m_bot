# US-AUTO Epic Registry

## Purpose
This registry is the durable epic-level source of truth for the US-AUTO automation epic.
It records which `US-AUTO-*` stories exist, how they relate to one another, which story artifact to open next, and the most conservative current status supported by committed repository evidence.

## Scope
Use this registry to track the minimum portfolio-level facts for the epic:
- story ID
- title
- short summary
- story type
- current status
- origin / relationship to other stories
- primary story artifact reference
- notes about uncertainty, splits, cancellation, or supersession

The registry does **not** replace story bundles. Story status must not exceed what is supported by committed bundle artifacts, documentation, or explicit follow-up references. When in doubt, use a more conservative status and explain uncertainty in `Notes`.
- Epic registry = epic-level lifecycle and status index.
- Bundle pack / active bundle = story-level execution artifact.
- `automation/runs/` = execution evidence.
- `05_followups.md` = story-local queue, but any resulting new `US-AUTO-*` story must also be recorded here.

## Status Legend
Use this compact status vocabulary for US-AUTO and future epic registries:
- `Planned` — referenced as future work, but no bundle artifacis committed yet.
- `Bundle Drafted` — a story is referenced and partially drafted, but the bundle is not yet ready for execution.
- `Bundle Ready` — a committed bundle artifact exists and appears ready to execute, but implementation evidence is not yet confirmed.
- `In Progress` — implementation work is underway.
- `Blocked` — known blocker prevents progress.
- `In Review` — implementation exists and is under review / gate processing.
- `Implemented` — committed repository evidence shows the story outcome landed.
- `Docs Only` — the story outcome is documentation/process only.
- `Split` — the original scope was intentionally divided into follow-up stories.
- `Cancelled` — the story was intentionally dropped.
- `Superseded` — the story number or scope was replacedoutcome.

## Type Legend
Keep story type vocabulary compact:
- `implementation`
- `docs-only`
- `follow-up`
- `enforcement`
- `split`
- `governance`

## Update Rules
Update this registry whenever any of the following happens:
1. A new `US-AUTO-*` story is created, drafted, or first referenced in a committed follow-up queue.
2. A story moves between lifecycle states such as `Planned`, `Bundle Ready`, `In Review`, `Implemented`, `Cancelled`, or `Superseded`.
3. A story is split into one or more follow-up stories.
4. A story number gains clarified history, such as a title change, supersession note, or conservative status correction.

When evidence is incomplete, prefer the most conservative status and explain the uncertainty in `Notes` instead of guessing.

## Registry Table

| US ID | Title | Summary | Type | Status | Origin | Story Artifact | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `US-AUTO-1` | Story bundle bootstrap automation | Bootstrapped reusable active story bundle creation. | implementation | Implemented | Initial US-AUTO workflow foundation. | `automation/bundles/active/US-AUTO-1/` | Supported by committed active bundle plus implementation commit history. |
| `US-AUTO-2` | Run story launcher by STORY_ID | Added story-first execution through `run_story.sh`. | implementation | Implemented | Follow-on from `US-AUTO-1`. | `automation/bundles/active/US-AUTO-2/` | Supported by active bundle, script presence, and commit `33b8f80`. |
| `US-AUTO-3` | Review story run artifacts | Added story-level review launcher workflow. | implementation | Implemented | Follow-on from `US-AUTO-1` and `US-AUTO-2`. | `automation/bundles/active/US-AUTO-3/` | Supported by active bundle, script presence, and commit `55dd8b1`. |
| `US-AUTO-4` | Lean story context for Codex runs | Reduced default Codex context size while preserving full-context mode. | implementation | Implemented | Follow-on optimization after early runner workflow stories. | `automation/bundles/active/US-AUTO-4/` | Supported by active bundle and commit `c64615b`. |
| `US-AUTO-5` | Automatic AI review for Codex runs | Added durable AI review execution for the latest story run. | implementation | Implemented | Follow-on from `US-AUTO-3`. | `automation/bundles/active/US-AUTO-5/` | Supported by active bundle, script presence, and commit `7343b0b`. |
| `US-AUTO-6` | AI review classification | Added durable review classification for AI review output. | implementation | Implemented | Follow-on from `US-AUTO-5`. | `automation/bundles/active/US-AUTO-6/` | Supported by active bundle, script presence, commits `55de1b9` and remediation `debbcc0`. |
| `US-AUTO-7` | Stable review evidence from commit range | Switched review evidence to stable commit-range based artifacts. | implementation | Implemented | Remediation follow-up after `US-AUTO-6`. | `automation/bundles/active/US-AUTO-7/` | Active bundle states it was created to remediate a false blocker discovered after merging `US-AUTO-6`. |
| `US-AUTO-8` | Isolated Codex runs via git worktree | Moved Codex execution into an isolated temporary worktree. | implementation | Implemented | Architectural hardening follow-up. | `automation/bundles/active/US-AUTO-8/` | Supported by active bundle and commit `4923abf`. |
| `US-AUTO-10` | Materialize isolated worktree output back to primary repository | Materialized isolated worktree changes into the main checkout before downstream steps. | implementation | Implemented | Follow-up from `US-AUTO-8`. | `automation/bundles/active/US-AUTO-10/` | Supported by active bundle, script behavior in repo, and commit `e801e4e`; later bundle-only commits refined the story artifacts. |
| `US-AUTO-11` | Repository Map Injection for Codex runs | Added `repository_map_runtime.md` injection to each run. | implementation | Implemented | Follow-up after worktree/materialization hardening. | `automation/bundles/active/US-AUTO-11/` | Supported by active bundle and commit `1a953d3`. |
| `US-AUTO-12` | Bundle Pack Materialization & Validation | Added canonical bundle packs plus materialization and validation flow. | implementation | Implemented | Expected next story from `US-AUTO-11`. | `automation/bundles/active/US-AUTO-12/` | Supported by bundle pack, active bundle, script presence, and commit `1f995aa`. |
| `US-AUTO-13` | Story Finalization Script | Added deterministic PR finalization and cleanup workflow. | implementation | Implemented | Follow-up queue item from `US-AUTO-12`. | `automation/bundles/active/US-AUTO-13/` | Supported by bundle pack, active bundle, script presence, and commit `36f46b1`. |
| `US-AUTO-14` | Allowed Files Guard | Enforced story file-scope boundaries after Codex materialization. | enforcement | Implemented | Follow-up queue item from `US-AUTO-12` / `US-AUTO-13`. | `automation/bundles/active/US-AUTO-14/` | Supported by bundle pack, active bundle, script presence, and commit `0df9bd0`. |
| `US-AUTO-15` | Finalize checks fallback *(title/history uncertain)* | Reserved follow-up slot whose meaning changed across references and was later absorbed by other documented story outcomes. | follow-up | Superseded | Initially referenced from `US-AUTO-12` / `US-AUTO-13` as `AI Review Gate`, and from `US-AUTO-14` as `Diff Size Guard`; later `US-AUTO-16` cites the number as finalize checks fallback. | — | The story number is documented, but no committed bundle pack or active bundle was found for `US-AUTO-15`. Because the title drifted across references and no explicit artifact maps the number to a final standalone bundle, this row is tracked as superseded rather than implemented. |
| `US-AUTO-16` AI Review Gate | Added a single machine-readable review gate step and gate result artifact. | implementation | Implemented | Follow-up after review automation and scope-enforcement stories. | `automation/bundles/active/US-AUTO-16/` | Supported by bundle pack, active bundle, script presence, and commit `169be89`. |
| `US-AUTO-17` | Repository Map Injection v2 | Expanded runtime repository maps with story-local context and anti-hallucination guidance. | implementation | Implemented | Follow-up to `US-AUTO-11` and `US-AUTO-16`. | `automation/bundles/active/US-AUTO-17/` | Supported by bundle pack, active bundle, and commit `16c17ab`. |
| `US-AUTO-18` | Pipeline Console UX Standard | Planned operator-facing console UX standardization. | follow-up | Planned | Referenced only in `US-AUTO-17` follow-up queue. | `automation/bundles/active/US-AUTO-17/05_followups.md` | No committed bundle pack, active bundle, or implementation artifact found. |
| `US-AUTO-19` | Failure Surfacing & Artifact Summaries | Added read-only run analysis for diagnosing workflow failures from one command. | implementation | Implemented | Follow-up queue item from `US-AUTO-17`. | `automation/bundles/active/US-AUTO-19/` | Supported by bundle pack, active bundle, `automation/scripts/analyze_story_run.sh`, and commit `60c4949`, whose message used a generic `US-AUTO-next` label instead of the final story number. |
| `US-AUTO-20` | Workflow Chaining & Resume | Planned workflow chaining / resume capabilities. | follow-up | Planned | Referenced in `US-AUTO-17` and `US-AUTO-19` follow-up queues. | `automation/bundles/active/US-AUTO-19/05_followups.md` | No committed bundle pack, active bundle, or implementation artifact found. |
| `US-AUTO-21` | Enforce Clean Commit Boundary Before Review Gate | Blocked review/gate on dirty, uncommitted materialized branch state. | enforcement | Implemented | Finalized follow-up after `US-AUTO-19`; earlier follow-up queues described this slot as long-running/logging work. | `automation/bundles/active/US-AUTO-21/` | Supported by bundle pack, active bundle, and commits `0dc58fa` and `00dadd5`; note that the story number's title evolved from earlier planning references. |
| `US-AUTO-22` | Atomic Task Isolation Rule for Codex Workflow | Added documentation-level atomic task isolation governance for the Codex workflow. | governance | Docs Only | Finalized follow-up after `US-AUTO-19`; earlier follow-up queues described this slot as review-result rendering. | `automation/bundles/active/US-AUTO-22/` | Supported by bundle pack, active bundle, and commits `1078ce2` and `8d58586`; this story is explicitly documentation/process only. |

## Maintenance Rules
- Before drafting or materializing a new `US-AUTO-*` story bundle, confirm the story already has a registry entry or add one first.
- When a story outcome changes during execution, review, split, cancellation, or follow-up creation, update this registry in the same change set.
- Before merge/finalization, reconcile the row against the committed story outcome so status, origin, artifact reference, and notes match reality.
- If a story number is referenced but still lacks enough evidence for a precise status, keep it in the registry with a conservative note rather than removing it.

## Evidence Boundary Notes
- This first version is populated only from committed repository evidence visible in active bundles, bundle packs, follow-up queues, existing docs, repository scripts, and git history.
- Numbering gaps with no committed evidence are intentionally not listed as story rows. At the time of writing, no committed `US-AUTO-9` artifact or follow-up reference was found.
- `US-AUTO-15`, `US-AUTO-21`, and `US-AUTO-22` each show scope/title drift across follow-up references; their rows preserve that history explicitly instead of normalizing it away.
