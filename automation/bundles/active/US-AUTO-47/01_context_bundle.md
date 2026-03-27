# Context Bundle

## Source of Truth
- run_story.sh
- analyze_story_run.sh
- US-AUTO-43 observation

## Current Code Reality
- Rerun may not converge
- Workspace changes reappear
- No boundary defined

## Architectural Intent
- Add boundary, not engine
- Keep fail-closed
- Preserve architecture

## Risks
- overreach
- false detection

## Acceptance Notes
- deterministic state
- explicit boundary

