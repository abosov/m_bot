# Статический сайт (landing) в FastAPI

## Где лежит сайт

Статические файлы находятся в директории `web/` в корне репозитория:

- `web/index.html` — главная страница лендинга.
- `web/assets/styles.css` — стили.
- `web/assets/app.js` — клиентский JS.
- `web/assets/` — каталог для дополнительных статических файлов (изображения/иконки).

## Как это подключено в приложении

В `web_server.py`:

- `GET /` отдаёт `web/index.html`.
- `GET /privacy` отдаёт `web/privacy.html` (публичная Privacy Policy на английском).
- `GET /terms` отдаёт `web/terms.html` (публичные Terms of Service на английском).
- `GET /privacy-ru` отдаёт `web/privacy-ru.html` (публичная политика конфиденциальности на русском).
- `GET /terms-ru` отдаёт `web/terms-ru.html` (публичные условия использования на русском).
- `/assets/*` раздаётся из `web/assets` через `StaticFiles`.
- `GET /site-health` возвращает `ok`.

Если директория `web/` или `web/index.html` отсутствуют, приложение не падает:
сайт просто не монтируется, а в лог пишется warning. Основные API/вебхуки бота продолжают работать.

## Локальная проверка

1. Запустить приложение (пример):

```bash
python main.py
```

или

```bash
uvicorn web_server:app --host 127.0.0.1 --port 8000
```

2. Проверить в браузере:

- `http://localhost:8000/` — открывается лендинг `Zumbot — Calendar Booking Automation`.
- `http://localhost:8000/assets/styles.css` — отдается CSS.
- `http://localhost:8000/assets/app.js` — отдается JS.
- `http://localhost:8000/privacy` — публичная страница `Privacy Policy — Zumbot`.
- `http://localhost:8000/terms` — публичная страница `Terms of Service — Zumbot`.
- `http://localhost:8000/privacy-ru` — публичная русская версия политики конфиденциальности.
- `http://localhost:8000/terms-ru` — публичная русская версия условий использования.
- `http://localhost:8000/site-health` — ответ `ok`.

## Деплой

Дополнительный деплой-пайплайн не нужен. Сайт деплоится вместе с кодом,
так как это статика в репозитории. Достаточно обычного ручного деплоя через:

- `scripts/vps_deploy.sh`.


## Публичные URL в продакшене

- `https://zumbot.ru/privacy` — публичная страница `Privacy Policy — Zumbot`.
- `https://zumbot.ru/terms` — публичная страница `Terms of Service — Zumbot`.
- `https://zumbot.ru/privacy-ru` — публичная русская версия политики конфиденциальности.
- `https://zumbot.ru/terms-ru` — публичная русская версия условий использования.
