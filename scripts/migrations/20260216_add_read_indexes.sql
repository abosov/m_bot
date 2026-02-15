-- Slot read-path indexes for specialist/client appointment lookups.
-- Uses CONCURRENTLY to reduce write blocking on large tables.
-- db_migrate.sh applies each migration file via `psql -f` without wrapping in BEGIN/COMMIT,
-- so CONCURRENTLY is allowed in this project's migration runner.

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_appointment_specialist_id_start_at_utc
ON appointment (specialist_id, start_at_utc);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_appointment_specialist_id_booking_state_start_at_utc
ON appointment (specialist_id, booking_state, start_at_utc);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_appointment_client_id_start_at_utc
ON appointment (client_id, start_at_utc);
