## Required Human Actions

Before starting implementation:

    - confirm current branch is not main;
    - confirm working tree is clean;
    - validate and materialize this bundle.

Before review-stage commands:

    - run analyze on the pinned run;
    - confirm working tree is clean;
    - confirm run evidence corresponds to current committed HEAD or use the allowed no-Codex refresh path.

Before push or PR:

    - restore automation/story_change_ledger.jsonl if it is the only unintended dirty file;
    - confirm git status is clean except intended committed changes;
    - push feature branch;
    - create implementation PR.

After implementation PR merge:

    - update local main;
    - perform registry closeout check;
    - create registry closeout PR if required;
    - merge registry closeout PR;
    - delete local and remote story branches;
    - confirm working tree clean.

## Completion Status

Draft bundle prepared.

Implementation not started.

Review not started.

Registry closeout not started.

Story remains open until implementation PR and registry closeout are complete.
