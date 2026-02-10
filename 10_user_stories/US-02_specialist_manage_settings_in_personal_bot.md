# US-02 — Управление настройками specialist через personal bot (MVP)

## Статус сценария
- **Implemented (текущий MVP):** базовые команды personal bot (`/start`, `/status`, `/help`) и role-guard для разделения specialist/client.
- **Planned/TODO:** полноценное управление расписанием, длительностью, буфером, отменами и заметками в personal bot.

## Цель
Дать specialist минимальный operational-интерфейс через personal bot и подготовить расширение до полного self-service управления приёмом.

## Что реализовано сейчас
1. Определение owner/specialist по Telegram actor.
2. Команда `/start`:
   - specialist: панель специалиста;
   - client: заглушка клиентского режима.
3. Команда `/status` (для specialist):
   - `specialist.status`;
   - статус personal bot;
   - статус Google OAuth;
   - данные calendar/smoke-test.
4. Команда `/help` с разделением по ролям.

## Planned/TODO (зафиксировано, не удалять)
1. Редактирование weekly availability.
2. Настройка `session_duration_min`.
3. Настройка `session_buffer_min`.
4. Управление подтверждёнными записями (отмена, private notes).
5. Расширенный Google reconnect flow из personal bot.

## Ограничения текущего MVP
- Полноценный booking-management через personal bot ещё не является завершённой функциональностью.
- Для диагностики и контроля используется `/status` и логи backend.
