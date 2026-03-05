# Onboarding architecture notes

## Specialist onboarding

### 2026-03-05: Split name and specialization
We collect specialist profile data as structured fields:
- public_name: the name displayed to clients
- specialization: profession for future filtering/catalog

Onboarding steps:
1) Name
2) Specialization
3) Personal bot token
4) Google Calendar connection (OAuth)
5) Calendar selection

Intervals/working hours are configured outside of this onboarding flow.
