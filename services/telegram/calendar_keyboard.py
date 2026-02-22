from aiogram import types


def build_calendar_selection_keyboard(
    calendars: list[dict],
    *,
    page: int,
    per_page: int,
) -> types.InlineKeyboardMarkup:
    total = len(calendars)
    rows: list[list[types.InlineKeyboardButton]] = [
        [types.InlineKeyboardButton(text="🔄 Обновить список", callback_data="calendar:refresh")]
    ]
    if total == 0:
        rows.append([types.InlineKeyboardButton(text="⬅️ Отмена", callback_data="calendar:cancel_select")])
        return types.InlineKeyboardMarkup(inline_keyboard=rows)

    pages = max(1, (total + per_page - 1) // per_page)
    page = max(0, min(page, pages - 1))
    start = page * per_page
    end = min(start + per_page, total)

    for idx in range(start, end):
        item = calendars[idx]
        summary = item.get("summary") or "Без названия"
        is_primary = bool(item.get("primary"))
        is_read_only = item.get("readOnly") or item.get("accessRole") == "reader"
        marker = ""
        if is_primary:
            marker = " (основной)"
        elif is_read_only:
            marker = " (только чтение)"
        rows.append(
            [
                types.InlineKeyboardButton(
                    text=f"📅 {summary}{marker}",
                    callback_data=f"calendar:pick:{idx}",
                )
            ]
        )

    nav: list[types.InlineKeyboardButton] = []
    if page > 0:
        nav.append(types.InlineKeyboardButton(text="⬅️ Prev", callback_data=f"calendar:page:{page - 1}"))
    if page < pages - 1:
        nav.append(types.InlineKeyboardButton(text="Next ➡️", callback_data=f"calendar:page:{page + 1}"))
    if nav:
        rows.append(nav)

    rows.append([types.InlineKeyboardButton(text="⬅️ Отмена", callback_data="calendar:cancel_select")])
    return types.InlineKeyboardMarkup(inline_keyboard=rows)
