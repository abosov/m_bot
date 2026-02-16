# Availability Optimization (Future Work)

## Future Optimization: Batch Availability Calculation

### Контекст

Текущая реализация availability в booking UI опирается на множественные вызовы `availability_service`:
- до `7×3` при выборе дня;
- до `3` при выборе диапазона.

В рамках FSM уже внедрено кэширование метаданных, что снижает повторные вызовы и уменьшает часть нагрузки на текущий pipeline.

### Ограничение текущего подхода

- Алгоритм всё ещё выполняет расчёты по каждому интервалу отдельно.
- При росте нагрузки и подключении Google Calendar API возможны задержки ответа.

### Planned Improvement (Future Development)

Планируется реализовать batch-функцию на уровне `availability_service`.

**Proposed API:**

```python
get_day_interval_availability(
    specialist_id: UUID,
    days: list[date],
    session_duration_min: int,
    specialist_tz: ZoneInfo
) -> dict[str, dict[str, int]]
```

**Return format:**

```json
{
  "2026-02-16": {
      "morning": 3,
      "day": 0,
      "evening": 2
  }
}
```

### Преимущества

- Один запрос к БД / календарю вместо множества.
- Единый расчёт busy-слотов за диапазон недели.
- Уменьшение latency ответа Telegram.
- Подготовка к масштабированию.

### Статус

- **Future development — not implemented.**
- **Приоритет:** Medium.
- Требует отдельного проектирования и нагрузочного тестирования.
