-- Admin read-path indexes for /admin/logs and /admin/heartbeats.
-- Uses CONCURRENTLY to reduce write blocking on large tables.
-- db_migrate.sh applies each migration file via `psql -f` without wrapping in BEGIN/COMMIT,
-- so CONCURRENTLY is allowed in this project's migration runner.

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_message_logs_created_at
ON message_logs (created_at);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_message_logs_tg_user_id_created_at
ON message_logs (tg_user_id, created_at);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_message_logs_is_error_created_at
ON message_logs (is_error, created_at);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_service_heartbeats_ts
ON service_heartbeats (ts);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_service_heartbeats_service_name_ts
ON service_heartbeats (service_name, ts);
