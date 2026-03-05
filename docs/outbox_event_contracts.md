# Outbox event contracts

This document defines outbox contracts for appointment notifications.

## Delivery model
- Producers write events to `outbox_events` in DB transaction.
- Outbox worker reads undelivered events and dispatches Telegram notifications.
- Scheduler can produce time-based reminder events.
- Personal bots do not schedule reminders directly.

---

## `appointment_client_reminder_24h`
- **Producer:** backend scheduler
- **Consumer:** outbox worker -> client personal bot sender

### Payload schema
| Key | Type | Required | Description |
|---|---|---:|---|
| `appointment_id` | `uuid` | yes | Appointment identity (internal). |
| `specialist_id` | `uuid` | yes | Specialist owner. |
| `client_id` | `uuid` | yes | Client owner. |
| `client_tg_user_id` | `int64` | yes | Telegram target user id. |
| `specialist_public_name` | `string` | yes | Public specialist name for client text. |
| `start_at_utc` | `string (date-time, UTC)` | yes | Appointment start datetime in UTC. |
| `client_timezone` | `string` | yes | IANA timezone to render local time for client. |
| `reminder_type` | `string` | yes (`h24`) | Reminder discriminator. |

---

## `appointment_client_reminder_2h`
- **Producer:** backend scheduler
- **Consumer:** outbox worker -> client personal bot sender

### Payload schema
| Key | Type | Required | Description |
|---|---|---:|---|
| `appointment_id` | `uuid` | yes | Appointment identity (internal). |
| `specialist_id` | `uuid` | yes | Specialist owner. |
| `client_id` | `uuid` | yes | Client owner. |
| `client_tg_user_id` | `int64` | yes | Telegram target user id. |
| `specialist_public_name` | `string` | yes | Public specialist name for client text. |
| `start_at_utc` | `string (date-time, UTC)` | yes | Appointment start datetime in UTC. |
| `client_timezone` | `string` | yes | IANA timezone to render local time for client. |
| `reminder_type` | `string` | yes (`h2`) | Reminder discriminator. |

---

## `appointment_client_confirmed` (new)
- **Producer:** backend client callback handler (24h reminder action `Подтвердить`)
- **Consumer:** outbox worker -> specialist personal bot sender

### Payload schema
| Key | Type | Required | Description |
|---|---|---:|---|
| `appointment_id` | `uuid` | yes | Appointment identity. |
| `specialist_id` | `uuid` | yes | Specialist owner. |
| `client_id` | `uuid` | yes | Client owner. |
| `client_tg_user_id` | `int64` | yes | Client telegram id. |
| `specialist_tg_user_id` | `int64` | yes | Specialist telegram id target. |
| `start_at_utc` | `string (date-time, UTC)` | yes | Appointment start datetime. |
| `client_display_name` | `string` | no | Optional preferred client name. |
| `client_username` | `string` | no | Optional telegram username. |
| `source` | `string` | yes | Value: `reminder_24h`. |

---

## `appointment_client_contact_specialist` (new)
- **Producer:** backend client callback handler (button `Написать специалисту` from reminders)
- **Consumer:** outbox worker -> specialist personal bot sender (and/or contact deeplink response to client flow)

### Payload schema
| Key | Type | Required | Description |
|---|---|---:|---|
| `appointment_id` | `uuid` | yes | Appointment identity. |
| `specialist_id` | `uuid` | yes | Specialist owner. |
| `client_id` | `uuid` | yes | Client owner. |
| `client_tg_user_id` | `int64` | yes | Client telegram id. |
| `specialist_tg_user_id` | `int64` | yes | Specialist telegram id target. |
| `start_at_utc` | `string (date-time, UTC)` | yes | Appointment start datetime. |
| `trigger` | `string` | yes | `reminder_24h` or `reminder_2h`. |

---

## `appointment_cancelled_by_client` (existing, payload extension)
- **Producer:** backend client cancellation handler
- **Consumer:** outbox worker -> specialist personal bot sender

### Payload schema (with extension)
| Key | Type | Required | Description |
|---|---|---:|---|
| `appointment_id` | `uuid` | yes | Appointment identity. |
| `specialist_id` | `uuid` | yes | Specialist owner. |
| `client_id` | `uuid` | yes | Client owner. |
| `start_at_utc` | `string (date-time, UTC)` | yes | Appointment start datetime. |
| `client_tg_user_id` | `int64` | no | Optional client telegram id. |
| `client_username` | `string` | no | Optional telegram username. |
| `comment` | `string` | no | Optional client cancellation comment from reminder flow (0..500 chars). |

## Contract-level constraints
- Event payload may include internal IDs, but user-facing message text must not contain appointment UUID/ID.
- Reminder events are emitted only for appointments currently in `confirmed`.
- Idempotency key is `(appointment_id, reminder_type)` enforced in DB reminder ledger.
