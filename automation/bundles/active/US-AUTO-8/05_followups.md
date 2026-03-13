# US-AUTO-8 Follow-ups

## Possible follow-up stories

### 1. Full bundle generation in one shot
Bundle creation/update should be fully atomic and generated as a complete bundle instead of file-by-file workflows.

### 2. Merge gate
A single command should decide whether a story is safe to merge.

### 3. Stage logging standard
Long-running automation scripts should emit explicit stage logs.

### 4. Configurable review base
Stable review evidence should eventually support configurable review bases instead of only `origin/main`.

## Not part of US-AUTO-8
- no product runtime logic changes
- no merge gate implementation
- no PR automation
- no full pipeline redesign beyond isolated run execution
