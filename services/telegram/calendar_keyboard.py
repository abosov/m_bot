from aiogram import types


def format_calendar_button_text(item: dict, *, is_current: bool = False) -> str:
    summary = (item.get("summary") or "Без названия").strip() or "Без названия"
    timezone = (item.get("timeZone") or "UTC").strip() or "UTC"
    current_marker = "\n✅ Current" if is_current else ""
    return f"📅 {summary}\n🌍 {timezone}{current_marker}"


def build_calendar_selection_keyboard(
    calendars: list[dict],
    *,
    page: int,
    per_page: int,
    current_calendar_id: str | None = None,
) -> types.InlineKeyboardMarkup:
    total = len(calendars)
    rows: list[list[types.InlineKeyboardButton]] = [
        [types.InlineKeyboardButton(text="🔄 Обновить список", callback_data="calendar:refresh")]
    ]
    if total == 0:
        rows.append([types.InlineKeyboardButton(text="⬅️ Назад", callback_data="calendar:cancel_select")])
        return types.InlineKeyboardMarkup(inline_keyboard=rows)

    pages = max(1, (total + per_page - 1) // per_page)
    page = max(0, min(page, pages - 1))
    start = page * per_page
    end = min(start + per_page, total)

    for idx in range(start, end):
        item = calendars[idx]
        item_id = item.get("id")
        rows.append(
            [
                types.InlineKeyboardButton(
                    text=format_calendar_button_text(
                        item,
                        is_current=bool(current_calendar_id and item_id == current_calendar_id),
                    ),
                    callback_data=f"calendar:pick:{idx}",
                )
            ]
        )

    nav: list[types.InlineKeyboardButton] = []
    if page > 0:
        nav.append(types.InlineKeyboardButton(text="⬅️ Назад", callback_data=f"calendar:page:{page - 1}"))
    if page < pages - 1:
        nav.append(types.InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"calendar:page:{page + 1}"))
    if nav:
        rows.append(nav)

    rows.append([types.InlineKeyboardButton(text="⬅️ Назад", callback_data="calendar:cancel_select")])
    return types.InlineKeyboardMarkup(inline_keyboard=rows)
