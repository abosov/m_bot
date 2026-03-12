US-PAY-2 PROMPT 1 — Bootstrap Codex CLI story automation framework and first story bundle

ROLE
You are the System Architect + Technical Writer + Developer + QA + Security Reviewer for Zumbot.

TASK
Create the initial repository structure and reusable templates for the Codex CLI-driven story execution workflow.
Use US-PAY-2 as the first real story bundle example.
Do NOT implement US-PAY-2 billing runtime yet. This prompt is only for process/bootstrap artifacts.

MANDATORY CONTEXT
Read and follow:
- docs/90_codex/CODEX_OPERATING_SYSTEM.md
- docs/90_codex/PROJECT_CONTEXT.md
- docs/90_codex/REPOSITORY_MAP.md
- docs/90_codex/PROJECT_CONTEXT_UPDATE_PROTOCOL.md
- skills/zumbot-user-story-workflow/SKILL.md
- docs/20_product/user_stories/EPIC_BILLING_YOOKASSA_MVP.md
- docs/30_architecture/billing_yookassa_subscription_mvp.md
- docs/50_integrations/yookassa.md

GOAL
Introduce a durable repository structure r:
- story bundles
- codex master prompts
- follow-up prompts
- review bundles
- step-by-step story execution checklist

Also create the first bundle for US-PAY-2 so future Codex runs can use it directly.

NON-GOALS
Do not:
- implement billing runtime logic
- modify payment routes
- modify web_server.py billing behavior
- modify database schema or migrations
- change deployment, CI/CD, infra, .github
- refactor unrelated files

SOURCE OF TRUTH
- Codex operating workflow: docs/90_codex/CODEX_OPERATING_SYSTEM.md
- Architecture and story boundaries: docs/30_architecture/billing_yookassa_subscription_mvp.md and docs/20_product/user_stories/EPIC_BILLING_YOOKASSA_MVP.md
- Existing integration doc may reflect legacy runtime and should be treated carefully, not as the target architecture source of truth

FILES ALLOWED TO CHANGE
Only these areas:
- docs/90_codex/**
- automation/**
- optionally docs/50_integrations/yookassa.md only if a minimal alignment note is necessary
- optionally docs/20_product/user_stories/EPIC_BILLING_YOOKASSA_MVP.md only if a minimal cross-reference is necessary

FILES NOT ALLOWED TO CHANGE
- web_server.py
- database.py
- scripts/migrations/**
- frontend/**
- services/billing runtime implementation
- telegram handlers
- deploy / infra / .github/**
- unrelated tests

IMPLEMENTATION RULES
- minimal patch only
- no unrelated refactor
- no formatting-only edits
- no speculative architecture beyond the process/bootstrap need
- create only the minimum necessary files for a durable story workflow
- prefer markdown for human-facing artifacts
- keep filenames stable and reusable

REQUIRED OUTPUT STRUCTURE

1) Create/ensure automation workspace directories:
- automation/prompts/master/
- automation/prompts/followups/
- automation/bundles/active/
- automation/bundles/archive/
- automation/output/
- automation/templates/
- automation/scripts/

2) Add permanent process docs under docs/90_codex/:
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md
- docs/90_codex/STORY_BUNDLE_SPEC.md
- docs/90_codex/REVIEW_CLASSIFICATION_RULES.md

3) Add reusable templates under automation/templates/:
- automation/templates/story_bundle_template.md
- automation/templates/codex_master_prompt_template.md
- automation/templates/followup_prompt_template.md
- automation/templates/review_prompt_template.md
- automation/templates/pr_description_template.md

4) Create first live story bundle for US-PAY-2 under:
- automation/bundles/active/US-PAY-2/00_story.md
- automation/bundles/active/US-PAY-2/01_context_bundle.md
- automation/bundles/active/US-PAY-2/02_file_scope.md
- automation/bundles/active/US-PAY-2/03_master_prompt.md
- automation/bundles/active/US-PAY-2/04_review_checklist.md
- automation/bundles/active/US-PAY-2/05_followups.md
- automation/bundles/active/US-PAY-2/06_manual_actions.md

CONTENT REQUIREMENTS

A. STORY_EXECUTION_CHECKLIST.md
Must define a stable SOP for:
- branch creation before any commit
- mandatory context doc reading
- repository map reconstruction
- source-of-truth identification
- FILES_ALLOWED_TO_CHANGE definition
- story bundle creation
- master prompt generation
- codex run
- pytest run
- review bundle collection
- review classification
- follow-up iteration
- PR / merge
- local main resync
- branch cleanup
- process improvement notes after each story

B. STORY_BUNDLE_SPEC.md
Must define the required sections for every bundle:
- story ID and title
- objective
- scope
- non-goals
- dependencies
- source of truth
- current code reality
- target architecture
- allowed files
- forbidden files
- risks
- manual actions
- acceptance notes

C. REVIEW_CLASSIFICATION_RULES.md
Must clearly define:
- MERGE BLOCKER
- MINOR IMPROVEMENT
- FOLLOW-UP STORY
with practical criteria for each

D. Template files
Must be generic and reusable, not US-PAY-2 specific

E. US-PAY-2 live bundle
Must accurately capture:
- US-PAY-2 objective: backend provider adapter + payment intent service
- non-goals: no public API endpoint, no UI wiring
- dependency on US-PAY-1 domain model
- current code reality: existing legacy BillingPurchase + SpecialistProfile.tariff_* flow exists
- target architecture: new billing_payments source-of-truth path
- route-layer work belongs later to US-PAY-3 / US-PAY-4
- docs mismatch note: docs/50_integrations/yookassa.md currently describes legacy flow and is not target architecture source of truth
- likely file scope for future implementation story:
  services/integrations/yookassa_client.py
  services/billing/subscriptions.py
  services/billing/__init__.py
  tests/test_billing_subscriptions.py
  tests/test_billing_subscription_flow.py
  docs/50_integrations/yookassa.md
  automation/bundles/active/US-PAY-2/*
- forbidden scope for future implementation story:
  web_server.py
  database.py schema
  migrations
  frontend
  deploy/infra/.github

F. US-PAY-2 master prompt draft
The created 03_master_prompt.md must be a real draft prompt for future implementation, but it must not be executed in this bootstrap prompt.

G. Manual actions file
06_manual_actions.md must clearly state:
- YooKassa cabinet access will be required later for real credentials
- no cabinet action is required for this bootstrap/process prompt itself

QUALITY BAR
- documents should be short, structured, and operational
- US-PAY-2 bundle should be directly usable by a human and by Codex
- do not introduce contradictions with CODEX_OPERATING_SYSTEM.md
- do not move or delete existing docs
- do not touch runtime code

OUTPUT FORMAT
Return:
1. changed files summary
2. rationale for structure
3. notes on how US-PAY-2 bundle should be used next
4. final diff
