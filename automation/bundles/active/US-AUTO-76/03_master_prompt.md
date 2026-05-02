## Role

You are working as a senior automation pipeline developer for the Zumbot / US-AUTO AI-dev workflow.

Your task is to implement US-AUTO-76 narrowly and safely.

You must preserve existing safety invariants and avoid starting adjacent stories.

## Goal

Fix classifier/review-gate scope semantics so approved story governance artifacts are not treated as merge blockers solely because they are governance artifacts.

The intended allowed governance artifact rule is:

Story governance artifacts are allowed when:

1. bundle pack is the source-of-truth artifact;
2. active bundle is materialized output;
3. registry update is an intentional lifecycle/governance update;
4. these files are explicitly scope-approved;
5. implementation/runtime review surface remains separately validated.

You must implement this without weakening review of runtime implementation files.

## Source of Truth

Use these files as the story source of truth:

- `automation/bundle_packs/US-AUTO-76.bundle.md`
- `automation/bundles/active/US-AUTO-76/00_story.md`
- `automation/bundles/active/US-AUTO-76/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-76/02_file_scope.md`
- `automation/bundles/active/US-AUTO-76/03_master_prompt.md`
- `automation/bundles/active/US-AUTO-76/04_review_checklist.md`
- `automation/bundles/active/US-AUTO-76/05_followups.md`
- `automation/bundles/active/US-AUTO-76/06_manual_actions.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

Use the existing code reality from:

- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `tests/test_classify_review_story_run.py`
- `tests/test_review_gate_story_run.py`

## Files Allowed To Change

You may change:

- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `tests/test_classify_review_story_run.py`
- `tests/test_review_gate_story_run.py`
- `automation/bundle_packs/US-AUTO-76.bundle.md`
- `automation/bundles/active/US-AUTO-76/**`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Files Not Allowed To Change

Do not change:

- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/run_story.sh`
- `automation/scripts/commit_story_artifacts.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/scripts/new_story_bundle.sh`
- `automation/scripts/escalate_story.sh`
- `automation/scripts/finalize_story.sh`
- `automation/story_change_ledger.jsonl`
- `docs/90_codex/US_AUTO_OPERATOR_GUIDE.md`
- `automation/scripts/next_step.sh`
- unrelated bundle packs
- unrelated active bundle directories
- unrelated docs

## Output

Implement the smallest safe change that satisfies the story.

Expected implementation behavior:

1. Active-story bundle pack path is recognized as an approved governance artifact:
   - `automation/bundle_packs/<STORY_ID>.bundle.md`

2. Active-story materialized bundle directory is recognized as approved governance output:
   - `automation/bundles/active/<STORY_ID>/**`

3. Registry update can be recognized as approved lifecycle/governance update only when explicitly scope-approved:
   - `docs/90_codex/epics/US-AUTO_REGISTRY.md`

4. Wrong-story governance artifacts are not automatically allowed:
   - `automation/bundle_packs/<OTHER_STORY>.bundle.md`
   - `automation/bundles/active/<OTHER_STORY>/**`

5. Implementation/runtime files remain separately validated and cannot hide behind governance artifact semantics.

6. Tests must prove:
   - active-story governance artifacts do not create classifier merge blockers when scope-approved;
   - wrong-story governance artifacts still block or remain suspicious;
   - registry path allowance remains explicit and does not become a broad docs wildcard;
   - review gate respects the classifier semantics without weakening existing checks.

7. Preserve existing CLI behavior, exit-code expectations, and external output contracts unless the test explicitly documents the new US-AUTO-76 contract.

Do not change tests to make failures disappear. Fix the implementation.

