# Zumbot Project Context

## Purpose
Zumbot is a SaaS platform for specialists that automates booking, scheduling, calendar sync, and supporting product flows through Telegram bots and web interfaces.

## Product Domains
- Public specialist pages
- Specialist onboarding and profile management
- Booking and calendar automation
- Google OAuth and calendar integration
- Billing and subscriptions
- Admin/support operations
- Website and legal/compliance pages

## Core Stack
- FastAPI
- PostgreSQL
- SQLAlchemy
- aiogram
- pytest
- Nginx / systemd / VPS deployment

## Architectural Principles
- Minimal patch only
- No unrelated refactor
- No formatting-only edits
- Respect existing architecture and naming
- SQL migrations are the source of truth for DB schema
- Business logic belongs in service/domain layers, not scattered across handlers/routes
- Endpoint contracts must stay explicit and documented
- Tests and docs must be updated with every meaningful change

## Source of Truth by Layer
- DB schema: SQL migrations
- API behavior: route definitions + tests + endpoint docs
- Domain logic: service layer
- UI behavior: component structure + user story acceptance criteria
- Operational behavior: scripts and deployment docs
- Product intent: user stories / epic docs

## Important Boundaries
- Do not broaden OAuth scopes unless explicitly requested
- Do not introduce hidden architectural refactors
- Do not change unrelated modules
- Do not silently rename public contracts
- Do not modify deployment/infrastructure unless story explicitly requires it
- Do not touch files outside explicitly allowed scope

## Repository Hot Zones
- backend / services
- frontend
- tests
- scripts
- docs

## Mandatory Delivery Rules
Every story should, where applicable:
- update implementation
- update tests
- update docs
- preserve backward compatibility unless story says otherwise
- include clear patch summary
- include explicit risks/assumptions

## Definition of Done
A story is not done until:
- code is implemented
- tests are added/updated
- docs are updated
- diff is reviewed
- manual checks are identified
- branch is ready for PR
