\pset pager off
\set ON_ERROR_STOP off

\echo === specialist ===
SELECT to_regclass('public.specialist') IS NOT NULL AS has_specialist \gset
\if :has_specialist
SELECT id, status, created_at, updated_at
FROM specialist
WHERE id::text = :'specialist_id';
\else
\echo SKIPPED_specialist.txt
\endif

\echo === specialist_profile ===
SELECT to_regclass('public.specialist_profile') IS NOT NULL AS has_specialist_profile \gset
\if :has_specialist_profile
SELECT specialist_id, specialist_timezone, session_duration_min, session_buffer_min, slot_step_min, max_sessions_per_day, cancel_window_hours
FROM specialist_profile
WHERE specialist_id::text = :'specialist_id';
\else
\echo SKIPPED_specialist_profile.txt
\endif

\echo === weekly_availability ===
SELECT to_regclass('public.weekly_availability') IS NOT NULL AS has_weekly_availability \gset
\if :has_weekly_availability
SELECT specialist_id, weekday, is_working,
       interval_1_start_local, interval_1_end_local,
       interval_2_start_local, interval_2_end_local,
       interval_3_start_local, interval_3_end_local
FROM weekly_availability
WHERE specialist_id::text = :'specialist_id'
ORDER BY weekday;
\else
\echo SKIPPED_weekly_availability.txt
\endif

\echo === telegram_bot ===
SELECT to_regclass('public.telegram_bot') IS NOT NULL AS has_telegram_bot \gset
\if :has_telegram_bot
SELECT specialist_id, username, status
FROM telegram_bot
WHERE specialist_id::text = :'specialist_id';
\else
\echo SKIPPED_telegram_bot.txt
\endif

\echo === specialist_calendar_settings ===
SELECT to_regclass('public.specialist_calendar_settings') IS NOT NULL AS has_specialist_calendar_settings \gset
\if :has_specialist_calendar_settings
SELECT specialist_id, calendar_id, calendar_time_zone
FROM specialist_calendar_settings
WHERE specialist_id::text = :'specialist_id';
\else
\echo SKIPPED_specialist_calendar_settings.txt
\endif

\echo === appointments_last_20 ===
SELECT to_regclass('public.appointments') IS NOT NULL AS has_appointments \gset
\if :has_appointments
SELECT *
FROM appointments
WHERE specialist_id::text = :'specialist_id'
LIMIT 20;
\else
\echo SKIPPED_appointments.txt
\endif

\echo === bookings_last_20 ===
SELECT to_regclass('public.bookings') IS NOT NULL AS has_bookings \gset
\if :has_bookings
SELECT *
FROM bookings
WHERE specialist_id::text = :'specialist_id'
LIMIT 20;
\else
\echo SKIPPED_bookings.txt
\endif
