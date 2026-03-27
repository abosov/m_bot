# US-AUTO-43: Context Bundle

## Source of Truth
- automation/scripts/ai_review_story_run.sh
- automation/scripts/classify_review_story_run.sh
- automation/scripts/review_gate_story_run.sh
- automation/scripts/analyze_story_run.sh

## Current Code Reality
- AI review validation is fail-closed across review/classify/gate/analyze
- invalid outputs cannot propagate to classification
- failure states are formally classified, including unreadable artifact handling

## Architectural Intent
- treat AI review as strict validation boundary
- enforce fail-closed behavior
- ensure deterministic pipeline behavior

## Risks
- scope drift into other pipeline stages
- incomplete validation
- hidden fallback paths

## Acceptance Notes
- validation enforced before classification
- failures block downstream execution
- behavior is deterministic
