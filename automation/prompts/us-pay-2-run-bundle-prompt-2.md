US-PAY-2 PROMPT 2 — Add per-run artifact bundle structure for Codex CLI workflow

ROLE
You are the System Architect + Developer + Technical Writer + QA for Zumbot.

TASK
Improve the Codex CLI automation workflow so each execution produces its own persistent run bundle directory with all review artifacts grouped together.
This is a process/tooling change only.
Do NOT implement billing runtime changes.

MANDATORY CONTEXT
Read and follow:
- docs/90_codex/CODEX_OPERATING_SYSTEM.md
- docs/90_codex/PROJECT_CONTEXT.md
- docs/90_codex/REPOSITORY_MAP.md
- docs/90_codex/PROJECT_CONTEXT_UPDATE_PROTOCOL.md
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md
- docs/90_codex/STORY_BUNDLE_SPEC.md
- docs/90_codex/REVIEW_CLASSIFICATION_RULES.md
- automation/bundles/active/US-PAY-2/00_story.md
- automation/bundles/active/US-PAY-2/01_context_bundle.md
- automation/bundles/active/US-PAY-2/02_file_scope.md
- automation/bundles/activUS-PAY-2/03_master_prompt.md

GOAL
Upgrade the Codex execution tooling so every run creates a dedicated directory like:

automation/runs/<STORY-ID>/<RUN-ID>/

and stores the full review package there.

NON-GOALS
Do not:
- implement US-PAY-2 billing logic
- modify web_server.py
- modify database schema or migrations
- change frontend
- change .github or deploy infrastructure
- refactor unrelated scripts

SOURCE OF TRUTH
- Story workflow rules: docs/90_codex/CODEX_OPERATING_SYSTEM.md
- Story bundle structure: docs/90_codex/STORY_BUNDLE_SPEC.md
- Existing automation workspace under automation/
- US-PAY-2 bundle as the first real story example

FILES ALLOWED TO CHANGE
- automation/run_codex_task.sh
- automation/scripts/**
- automation/templates/**
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md
- docs/90_codex/STORY_BUNDLE_SPEC.md
- automation/bundles/active/US-PAY-2/**
- optionally create automation/runs/.gitkeep
- optionally add minimal README/notes under automation/ if strictly helpful

FILES NOT ALLOWED TO CHANGE
- web_server.py
- database.py
- scripts/migrations/**
- frontend/**
- services/billing/**
- deploy / infra / .github/**
- unrelated tests

IMPLEMENTATION RULES
- minimal patch only
- no unrelated refactor
- preserve current workflow behavior where possible
- extend the existing script rather than replacing the whole process
- prefer stable, human-readable directory naming
- generated run bundle must be easy to zip/send for external review
- keep old automation/output compatibility only if clearly necessary; otherwise document the new source of truth

REQUIRED CHANGES

1) Introduce per-run artifact storage:
Create a run bundle layout:
- automation/runs/<STORY-ID>/<RUN-ID>/

Where:
- STORY-ID is derived from prompt path or bundle path when possible
- RUN-ID is deterministic enough for humans, e.g. timestamp + prompt label

2) Each run bundle must contain:
- manifest.md
- story_context.md
- codex_prompt.md
- codex_last_message.txt
- codex.log
- diff.patch
- diff.stat
- changed_files.txt
- pytest.txt
- review_bundle.md
- chatgpt_review_prompt.md
- run_meta.txt

3) manifest.md must summarize:
- story ID
- prompt file path
- branch
- starting HEAD sha
- run timestamp
- run directory path
- artifact list
- pytest command used
- codex exit code
- whether changed files were detected

4) story_context.md must be generated from the active story bundle and include a compact review-ready summary:
- story ID/title
- objective
- scope
- non-goals
- source of truth
- allowed files
- forbidden files
- current code reality
- target architecture
- acceptance notes
For US-PAY-2, use the bundle files already created under automation/bundles/active/US-PAY-2/.

5) codex_prompt.md must store the exact prompt used for the run.

6) Update workflow docs as needed:
- STORY_EXECUTION_CHECKLIST.md should mention per-run bundle creation and archive path
- STORY_BUNDLE_SPEC.md should distinguish between:
  - persistent story bundle in automation/bundles/active/<STORY-ID>/
  - execution artifacts in automation/runs/<STORY-ID>/<RUN-ID>/

7) Preserve usability:
The script should still be runnable with one command similar to:
bash automation/run_codex_task.sh <prompt-file>

8) Review ergonomics:
The resulting run directory should be the single folder a user can inspect or send for review.

DESIGN PREFERENCE
Preferred architecture:
- persistent planning artifacts live in automation/bundles/active/<STORY-ID>/
- actual execution artifacts live in automation/runs/<STORY-ID>/<RUN-ID>/

TESTING
Add/update only minimal tests if the repository already has a matching pattern for script/tooling checks.
If no such pattern exists, validate via script output and documentation updates only.
At minimum ensure the script is shell-safe and paths are handled correctly.

OUTPUT FORMAT
Return:
1. changed files summary
2. design rationale
3. example resulting run path for US-PAY-2
4. notes about backward compatibility with automation/output
5. final diff
