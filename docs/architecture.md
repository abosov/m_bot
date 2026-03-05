# Architecture

## Telegram message formatting

Dynamic values in Telegram messages must be escaped for MarkdownV2 using `escape_markdown_v2()`.

## Client appointment scenarios

- Client appointment scenarios, including reminders US-REM-1: `docs/user_flows/client_appointments.md`.

## Outbox contracts

- Appointment outbox event contracts: `docs/outbox_event_contracts.md`.
- Time-based reminders must be produced only by scheduler and delivered only via outbox worker.
