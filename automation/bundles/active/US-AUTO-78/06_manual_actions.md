## Required Human Actions

Before starting this story, verify the pre-story gate:

    git status --short
    gh pr list --state open --json number,title,headRefName,baseRefName,url
    git branch --show-current

Expected:

- clean working tree or only intentional US-AUTO-78 docs/governance changes;
- no conflicting open PRs;
- current branch is `docs/us-auto-78-roadmap-orchestration-alignment`.

After creating this bundle pack, materialize and validate it:

    automation/scripts/materialize_story_bundle.sh US-AUTO-78
    automation/scripts/validate_story_bundle.sh US-AUTO-78

Review scope:

    git status --short
    git diff -- docs/90_codex/epics/US-AUTO_REGISTRY.md docs/90_codex/US_AUTO_OPERATOR_GUIDE.md automation/bundle_packs/US-AUTO-78.bundle.md automation/bundles/active/US-AUTO-78

Commit the docs/governance changes and story artifacts together.

Then run the story only if the bundle is valid and the working branch is not `main`:

    automation/scripts/run_story.sh US-AUTO-78

## Completion Status

Not complete until:

- bundle validates;
- allowed docs and story artifacts are committed;
- run/analyze/review path completes for this docs/governance story;
- PR is merged;
- branch cleanup is done;
- local `main` is updated;
- registry closeout is checked or explicitly deemed not required beyond this story's own registry update.
