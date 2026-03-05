# Database schema (selected tables)

## specialist
- specialist_id (uuid, pk)
- public_name (text, nullable)
- specialization (text, nullable)
- telegram_bot_token (text, nullable)
- calendar_id (text, nullable)
- status (enum, not null)

## Notes
- `specialist.specialization` is nullable and added via SQL migration `scripts/migrations/20260305_add_specialist_specialization.sql`.
- ORM mirrors this as a nullable text field in `database.py`.
