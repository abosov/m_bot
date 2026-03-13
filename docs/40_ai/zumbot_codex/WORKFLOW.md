# Zumbot Codex Workflow

## Goal
Use Codex CLI safely and consistently for implementing user stories with minimal hallucinations and minimal scope drift.

## Flow

### 1. Prepare the story
- confirm the user story exists in docs
- confirm acceptance criteria
- confirm non-goals
- confirm expected tests/docs impact

### 2. Prepare context
- check PROJECT_CONTEXT.md
- identify likely repo areas
- identify exact files to inspect first

### 3. Run Story Controller
Input:
- user story
- project context
- relevant repository map / known files

Output:
- FILES_ALLOWED_TO_CHANGE
- MASTER PROMPT
- REVIEW PROMPT
- FOLLOW-UP PROMPT skeleton

### 4. Run Codex CLI with MASTER PROMPT
Codex should:
- inspect exact files
- propose minimal implementation
- implement only scoped change
- update focused tests
- update docs if required

### 5. Review the diff
Use REVIEW PROMPT against the resulting diff.

### 6. Apply corrections
If review finds issues, use FOLLOW-UP PROMPT with exact required fixes.

### 7. Validate locally
Run:
- targeted pytest
- broader pytest if needed
- manual checks relevant to the story

Always state where commands run:
- local
- VPS

### 8. Prepare branch
- inspect final diff
- commit
- git pushup
- open PR

## Non-Negotiable Rules
- no direct push to main
- minimal patch only
- no unrelated refactor
- no formatting-only edits
- no touching files outside allowed scope
- docs and tests must stay aligned with code

## Practical Heuristic
For every story ask:
1. What is the smallest correct patch?
2. What is the source of truth?
3. What must not change?
4. What proves this works?

## Branch Hygiene Rules

- Start every story from a clean and up-to-date local `main`.
- One story = one dedicated branch.
- Never commit directly to `main`.
- Merge through PR only.

After merge:

git checkout main
git pull --ff-only
git branch -d <story-branch>

Remote branch must also be deleted.

Final expected local state:

* main

No additional branches must remain locally after a story is completed.

