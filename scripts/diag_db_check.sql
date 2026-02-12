\pset pager off
\set ON_ERROR_STOP on

WITH input AS (
  SELECT :'specialist_id'::text AS specialist_id
),
specialist_row AS (
  SELECT s.id::text AS specialist_id, s.status::text AS specialist_status
  FROM specialist s
  JOIN input i ON s.id::text = i.specialist_id
),
profile_row AS (
  SELECT sp.specialist_id::text AS specialist_id,
         sp.specialist_timezone::text AS specialist_timezone,
         sp.session_duration_min,
         sp.session_buffer_min,
         sp.slot_step_min,
         sp.max_sessions_per_day,
         sp.cancel_window_hours
  FROM specialist_profile sp
  JOIN input i ON sp.specialist_id::text = i.specialist_id
),
calendar_row AS (
  SELECT scs.specialist_id::text AS specialist_id,
         scs.calendar_id::text AS calendar_id,
         scs.calendar_time_zone::text AS calendar_time_zone
  FROM specialist_calendar_settings scs
  JOIN input i ON scs.specialist_id::text = i.specialist_id
),
weekly_rows AS (
  SELECT wa.specialist_id::text AS specialist_id,
         wa.weekday,
         wa.is_working,
         wa.interval_1_start_local,
         wa.interval_1_end_local,
         wa.interval_2_start_local,
         wa.interval_2_end_local,
         wa.interval_3_start_local,
         wa.interval_3_end_local
  FROM weekly_availability wa
  JOIN input i ON wa.specialist_id::text = i.specialist_id
),
bot_rows AS (
  SELECT tb.specialist_id::text AS specialist_id,
         tb.status::text AS bot_status
  FROM telegram_bot tb
  JOIN input i ON tb.specialist_id::text = i.specialist_id
)
SELECT 'specialist_exists' AS key, (EXISTS(SELECT 1 FROM specialist_row))::text AS value
UNION ALL
SELECT 'specialist_status', COALESCE((SELECT specialist_status FROM specialist_row LIMIT 1), '')
UNION ALL
SELECT 'bot_exists', (EXISTS(SELECT 1 FROM bot_rows))::text
UNION ALL
SELECT 'bot_status', COALESCE((SELECT bot_status FROM bot_rows ORDER BY specialist_id LIMIT 1), '')
UNION ALL
SELECT 'calendar_exists', (EXISTS(SELECT 1 FROM calendar_row))::text
UNION ALL
SELECT 'calendar_id', COALESCE((SELECT calendar_id FROM calendar_row LIMIT 1), '')
UNION ALL
SELECT 'calendar_time_zone', COALESCE((SELECT calendar_time_zone FROM calendar_row LIMIT 1), '')
UNION ALL
SELECT 'profile_exists', (EXISTS(SELECT 1 FROM profile_row))::text
UNION ALL
SELECT 'profile_timezone', COALESCE((SELECT specialist_timezone FROM profile_row LIMIT 1), '')
UNION ALL
SELECT 'session_duration_min', COALESCE((SELECT session_duration_min::text FROM profile_row LIMIT 1), '')
UNION ALL
SELECT 'session_buffer_min', COALESCE((SELECT session_buffer_min::text FROM profile_row LIMIT 1), '')
UNION ALL
SELECT 'slot_step_min', COALESCE((SELECT slot_step_min::text FROM profile_row LIMIT 1), '')
UNION ALL
SELECT 'max_sessions_per_day', COALESCE((SELECT max_sessions_per_day::text FROM profile_row LIMIT 1), '')
UNION ALL
SELECT 'cancel_window_hours', COALESCE((SELECT cancel_window_hours::text FROM profile_row LIMIT 1), '')
UNION ALL
SELECT 'weekly_count', COALESCE((SELECT COUNT(*)::text FROM weekly_rows), '0')
UNION ALL
SELECT 'weekly_invalid_xor_count', COALESCE((
  SELECT COUNT(*)::text
  FROM weekly_rows
  WHERE
    ((interval_1_start_local IS NULL) <> (interval_1_end_local IS NULL)) OR
    ((interval_2_start_local IS NULL) <> (interval_2_end_local IS NULL)) OR
    ((interval_3_start_local IS NULL) <> (interval_3_end_local IS NULL))
), '0')
UNION ALL
SELECT 'weekly_invalid_rows', COALESCE((
  SELECT string_agg(
    format(
      'weekday=%s i1=%s/%s i2=%s/%s i3=%s/%s',
      weekday,
      COALESCE(interval_1_start_local::text, 'NULL'),
      COALESCE(interval_1_end_local::text, 'NULL'),
      COALESCE(interval_2_start_local::text, 'NULL'),
      COALESCE(interval_2_end_local::text, 'NULL'),
      COALESCE(interval_3_start_local::text, 'NULL'),
      COALESCE(interval_3_end_local::text, 'NULL')
    ), '; '
  )
  FROM weekly_rows
  WHERE
    ((interval_1_start_local IS NULL) <> (interval_1_end_local IS NULL)) OR
    ((interval_2_start_local IS NULL) <> (interval_2_end_local IS NULL)) OR
    ((interval_3_start_local IS NULL) <> (interval_3_end_local IS NULL))
), '')
UNION ALL
SELECT 'policy_persisted', CASE
  WHEN to_regclass('public.booking_policy') IS NOT NULL THEN 'true'
  WHEN EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema='public'
      AND table_name='specialist_profile'
      AND column_name IN ('next_day_cutoff_hour', 'next_day_cutoff_time', 'booking_cutoff_hour')
  ) THEN 'true'
  ELSE 'false'
END
;
