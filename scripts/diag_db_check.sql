WITH input AS (
  SELECT :'specialist_id'::text AS specialist_id
)
SELECT 'SPEC' AS row_type,
       COALESCE(s.status::text, '') AS c1,
       '' AS c2,
       '' AS c3,
       '' AS c4,
       '' AS c5,
       '' AS c6,
       '' AS c7,
       '' AS c8
FROM input i
LEFT JOIN specialist s ON s.id::text = i.specialist_id

UNION ALL
SELECT 'BOT' AS row_type,
       COALESCE(tb.status::text, '') AS c1,
       '' AS c2,
       '' AS c3,
       '' AS c4,
       '' AS c5,
       '' AS c6,
       '' AS c7,
       '' AS c8
FROM input i
LEFT JOIN LATERAL (
  SELECT status
  FROM telegram_bot tb
  WHERE tb.specialist_id::text = i.specialist_id
  ORDER BY tb.id
  LIMIT 1
) tb ON TRUE

UNION ALL
SELECT 'CAL' AS row_type,
       COALESCE(scs.calendar_id::text, '') AS c1,
       COALESCE(scs.calendar_time_zone::text, '') AS c2,
       '' AS c3,
       '' AS c4,
       '' AS c5,
       '' AS c6,
       '' AS c7,
       '' AS c8
FROM input i
LEFT JOIN specialist_calendar_settings scs ON scs.specialist_id::text = i.specialist_id

UNION ALL
SELECT 'PROFILE' AS row_type,
       COALESCE(sp.specialist_timezone::text, '') AS c1,
       COALESCE(sp.session_duration_min::text, '') AS c2,
       COALESCE(sp.session_buffer_min::text, '') AS c3,
       COALESCE(sp.cancel_window_hours::text, '') AS c4,
       COALESCE(sp.max_sessions_per_day::text, '') AS c5,
       COALESCE(sp.slot_step_min::text, '') AS c6,
       '' AS c7,
       '' AS c8
FROM input i
LEFT JOIN specialist_profile sp ON sp.specialist_id::text = i.specialist_id

UNION ALL
SELECT 'WA' AS row_type,
       wa.weekday::text AS c1,
       COALESCE(wa.is_working::text, '') AS c2,
       COALESCE(wa.interval_1_start_local::text, '') AS c3,
       COALESCE(wa.interval_1_end_local::text, '') AS c4,
       COALESCE(wa.interval_2_start_local::text, '') AS c5,
       COALESCE(wa.interval_2_end_local::text, '') AS c6,
       COALESCE(wa.interval_3_start_local::text, '') AS c7,
       COALESCE(wa.interval_3_end_local::text, '') AS c8
FROM weekly_availability wa
JOIN input i ON wa.specialist_id::text = i.specialist_id
ORDER BY row_type, c1;
