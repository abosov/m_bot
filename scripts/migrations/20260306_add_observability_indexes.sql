-- Observability read-path indexes for Admin Console (US-AD-6).
-- Postgres migration (executed by scripts/db_migrate.sh via psql).
-- Uses CREATE INDEX IF NOT EXISTS for idempotency.

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_message_logs_specialist_id_created_at
ON message_logs (specialist_id, created_at);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_message_logs_bot_id_created_at
ON message_logs (bot_id, created_at);

-- ServiceHeartbeat uses `created_at` in requirements, but the current schema may still use `ts`.
-- Keep migration safe for both variants via conditional dynamic DDL.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'service_heartbeats'
          AND column_name = 'created_at'
    ) THEN
        EXECUTE 'CREATE INDEX IF NOT EXISTS ix_service_heartbeats_created_at ON service_heartbeats (created_at)';
        EXECUTE 'CREATE INDEX IF NOT EXISTS ix_service_heartbeats_service_name_created_at ON service_heartbeats (service_name, created_at)';
    ELSIF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'service_heartbeats'
          AND column_name = 'ts'
    ) THEN
        EXECUTE 'CREATE INDEX IF NOT EXISTS ix_service_heartbeats_created_at ON service_heartbeats (ts)';
        EXECUTE 'CREATE INDEX IF NOT EXISTS ix_service_heartbeats_service_name_created_at ON service_heartbeats (service_name, ts)';
    ELSE
        RAISE NOTICE 'service_heartbeats has neither created_at nor ts; skipping heartbeat index creation';
    END IF;
END;
$$;
