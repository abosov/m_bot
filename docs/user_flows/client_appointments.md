# Client appointment scenarios

## Scope
This document describes client-side appointment flows in personal specialist bots, including reminder behavior.

## Existing baseline (context)
- Booking and cancellation flows are defined in user stories US-03 and US-04.
- Delivery of Telegram notifications must go through `scheduler -> outbox_events -> outbox worker -> Telegram sender`.
- Scheduler is the only component allowed to plan reminder timing.

## Reminders (US-REM-1)

### User Story
- **ID:** US-REM-1
- **Title:** Client reminders 24h/2h
- **Actors:**
  - client
  - backend (scheduler)
  - outbox worker
  - personal bot specialist

### Preconditions
- `appointment.booking_state == confirmed`.
- Client has `tg_user_id`.
- Specialist has personal bot.
- `start_at_utc` is stored in UTC.

### Trigger A — 24h before `start_at_utc`
Scheduler selects due appointments and emits outbox event `appointment_client_reminder_24h`.

Client receives message with confirmation question and buttons:
- `Подтвердить`
- `Отменить`
- `Написать специалисту`

Callback contract:
- `client_rem:confirm:{appointment_id}`
- `client_rem:cancel:{appointment_id}`
- `client_rem:contact:{appointment_id}`

#### 24h cancellation branch
1. Client taps `Отменить`.
2. Bot checks `cancel_window_hours` against remaining time to `start_at_utc`.
3. If cancellation is allowed:
   - show extra step with buttons:
     - `Оставить комментарий специалисту`
     - `Без комментария`
   - callback contract for step:
     - `client_rem:cancel_comment:yes:{appointment_id}`
     - `client_rem:cancel_comment:no:{appointment_id}`
   - optional comment is accepted as one message (up to 500 chars), then cancellation is processed.
4. If cancellation is not allowed (< N hours):
   - do not cancel in bot;
   - show: `Отмена недоступна менее чем за N часов до начала. Напишите специалисту.`

### Trigger B — 2h before `start_at_utc`
Scheduler selects due appointments and emits outbox event `appointment_client_reminder_2h`.

Client receives a simple reminder and one button:
- `Написать специалисту`

### Constraints
- Reminder is sent once per pair `(appointment_id, reminder_type)`.
- If appointment is not `confirmed` at send time (including canceled), reminder is skipped.
- For 24h reminder, cancellation action always respects `cancel_window_hours`.
- Reminder and callback texts must not expose `appointment_id`/UUID.
- Planning is done only by scheduler; personal bot does not run reminder timers.

### Acceptance Criteria
1. For a confirmed appointment with valid client `tg_user_id`, scheduler emits exactly one 24h reminder event and exactly one 2h reminder event per appointment.
2. Duplicate scheduler runs do not cause duplicate reminder delivery for same `(appointment_id, reminder_type)`.
3. If appointment state becomes non-confirmed before due time, no reminder is delivered.
4. 24h reminder message includes three buttons: `Подтвердить`, `Отменить`, `Написать специалисту`.
5. On `Отменить`, bot performs `cancel_window_hours` check at action time.
6. If less than `cancel_window_hours` remains, cancellation is blocked with explanatory message and contact option.
7. If cancellation is allowed, bot asks whether to leave specialist comment (`Оставить комментарий специалисту` / `Без комментария`).
8. Optional comment is delivered to specialist through outbox payload and is not required to be persisted in a separate DB table.
9. 2h reminder sends informational text and `Написать специалисту` button only.
10. No message text contains internal appointment identifiers (`appointment_id`, UUID).
11. End-to-end dispatch path is `scheduler -> outbox_events -> outbox worker -> bot delivery` only.

## Data architecture decisions (idempotency)

### Reminder delivery ledger table
Introduce DB table (via SQL migrations) to keep idempotent reminder fact:
- `appointment_id` (FK -> appointments.id, required)
- `reminder_type` (`h24 | h2`, required; enum or constrained text)
- `sent_at_utc` (timestamp with timezone, nullable until delivered)
- `created_at_utc` (timestamp with timezone, required, default now UTC)
- `UNIQUE (appointment_id, reminder_type)`
- DB defaults for reminder ledger are defined in SQL migration (`migrations/sql/20260309_add_appointment_reminder.sql`), not in ORM fields.

### Why this does not create a second source of truth
- Appointment lifecycle state remains in `appointments` table.
- Reminder ledger stores only technical delivery fact (`scheduled/sent`) for idempotency.
- Business truth (`confirmed/canceled/...`) is still read from `appointments` at scheduling/sending time.
- Therefore ledger is an implementation detail for reliable delivery, not a competing domain state.

### Comment persistence decision
- `comment_text` for cancellation from reminder flow is **not** stored in dedicated DB table.
- Comment is passed in outbox payload to specialist notification consumer only.
- Rationale: avoid extra persistence surface for non-critical transient note, keep single domain source in appointment aggregate + outbox audit trail.

## UX copy (RU)

### 24h reminder message
`У вас встреча с {specialist_public_name} {дата/время в TZ клиента}. Подтвердите, пожалуйста.`

Buttons:
- `Подтвердить`
- `Отменить`
- `Написать специалисту`

### 2h reminder message
`Напоминание: встреча с {specialist_public_name} {дата/время в TZ клиента} через 2 часа.`

Button:
- `Написать специалисту`

### Cancel comment step
Text:
`Хотите оставить комментарий специалисту?`

Buttons:
- `Оставить комментарий специалисту`
- `Без комментария`

### Comment input
`Напишите комментарий одним сообщением (до 500 символов).`

### After confirmation by client
To client:
`Спасибо! Отметили, что вы придёте.`

To specialist (notification):
`Клиент подтвердил, что придёт на встречу.`

### After cancellation by client
To client:
`Запись отменена.`

To specialist:
`Клиент отменил запись. {Комментарий: <text>}` (part with comment is included only when comment exists).

### Contact specialist action
`Написать специалисту` uses neutral contact flow (no scheduling logic, no reminder timers).

Micro-flow:
- client gets: `Передал специалисту просьбу написать вам.`
- specialist gets outbox notification with client identity and appointment time.

## Security checklist (reminder callbacks)
- Ownership check is mandatory for each callback: action is allowed only when `callback.from_user.id` matches appointment client and `specialist_id` context.
- State check is mandatory: reminder actions operate only on актуальная `confirmed` appointment; otherwise action is rejected with alert and no side effects.
- Cancel action must always respect `cancel_window_hours` policy.
- Contact action has anti-spam guard: one contact signal per appointment per 5-minute bucket (`idempotency_key`).
- Logs must not include raw comment text or full callback payloads with personal data; comment logging is length-only.
