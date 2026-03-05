# Specialist onboarding flow

## Goal
Collect specialist profile data for correct display to clients and future filtering by profession.

## Steps (no working-hours/intervals here)
1. Name (display name)
2. Specialization
3. Personal bot token
4. Google Calendar connection (OAuth)
5. Calendar selection

## Data collected
- specialist.public_name (step 1)
- specialist.specialization (step 2)
- specialist.telegram_bot_token (step 3)
- google oauth token (step 4)
- specialist.calendar_id (step 5)

## Notes
- Specialization is stored as a separate field to enable future filters/catalog.
- Database schema changes must be introduced via SQL migrations.

- This onboarding does not configure working hours/intervals.
- FSM state for step 2: `ENTER_SPECIALIZATION` (implemented as `waiting_for_specialization` in current handler state names).

## Calendar selection UI
Calendars are shown as:
`📅 <Calendar name> (<Timezone>)`
Example: `📅 Alex psy (Europe/Moscow)`
