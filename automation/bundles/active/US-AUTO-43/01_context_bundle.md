# US-AUTO-43: Context Bundle

## Source of Truth
- automation/scripts/ai_review_story_run.sh
- automation/scripts/classify_review_story_run.sh
- automation/scripts/review_gate_story_run.sh
- automation/scripts/analyze_story_run.sh

## Current Code Reality
- validation before classification is inconsistent
- invalid outputs may propagate
- failure states are not formally classified

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

