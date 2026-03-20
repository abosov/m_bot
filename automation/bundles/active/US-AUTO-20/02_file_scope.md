# US-AUTO-20: File Scope

## Files Allowed To Change
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/**`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `tests/**`
- `automation/bundle_packs/**`
- `automation/bundles/active/US-AUTO-20/**`

## Files Not Allowed To Change
- `backend/**`
- `migrations/**`
- `web/**`
- `admin_api.py`
- `database.py`
- product application flows unrelated to automation

## Scope Notes
- Keep chaining/resume logic deterministic and artifact-driven.
- Reuse existing stage semantics where possible.
- Do not expand into broader UX redesign or autonomous execution.

