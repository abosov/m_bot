# Zumbot Repository Map

This document provides a structural overview of the repository for AI tools such as Codex and GPT.

AI must respect this architecture and prefer minimal, in-scope changes only.

## Core Repository Areas

### backend / services
Business logic and orchestration layer.

Rules:
- orchestrates domain operations
- may call repositories or integration clients
- should not scatter business rules across unrelated layers

### services
Core service/domain logic used by the product.

Examples:
- billing
- integrations
- public specialist data
- scheduling flows

Rules:
- business behavior should stay explicit
- external provider handling should stay isolated
- state transitions should be clear and auditable

### database / migrations
Database schema source of truth.

Rules:
- SQL migrations are authoritative
- schema changes must be reflected through migrations
- code must align with actual migration-defined schema

### frontend
UI layer.

Rules:
- UI should not hide business-critical logic
- component changes should stay scoped
- preserve existing UX patterns unless the story explicitly changes them

### handlers
Telegram bot interaction layer.

Rules:
- handlers should stay thin where possible
- orchestration belongs in services
- avoid embedding domain rules directly in bot handlers

### tests
Verification layer.

Rules:
- add or update focused tests for changed behavior
- prefer smallest sufficient test coverage
- reuse existing patterns and fixtures

### docs
Documentation and operational guidance.

Important areas:
- docs/20_product/
- docs/30_architecture/
- docs/40_ai/
- docs/90_codex/

## AI Working Rules

1. Minimal patch only.
2. Do not invent new architecture if existing structure supports the change.
3. Do not touch files outside explicitly allowed scope.
4. Prefer existing files over new files.
5. Keep business logic in the appropriate service/domain layer.
6. Keep external API logic isolated.
7. Treat migrations as the source of truth for DB schema.
8. Update tests and docs when behavior changes.

## Practical Use

Before implementing any user story, AI should read:
- docs/40_ai/zumbot_codex/PROJECT_CONTEXT.md
- docs/40_ai/zumbot_codex/REPOSITORY_MAP.md

Then AI should identify:
- exact files to inspect first
- exact files allowed to change
- layers that must not be changed
