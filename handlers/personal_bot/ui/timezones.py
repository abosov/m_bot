from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

TZ_PAGES: dict[int, list[tuple[str, str]]] = {
    1: [
        ("UTC−1 — Понта-Делгада", "Atlantic/Azores"),
        ("UTC-0 — Лондон", "Europe/London"),
        ("UTC+1 — Берлин", "Europe/Berlin"),
        ("UTC+2 — Афины", "Europe/Athens"),
        ("UTC+3 — Москва", "Europe/Moscow"),
        ("UTC+4 — Дубай", "Asia/Dubai"),
        ("UTC+5 — Ташкент", "Asia/Tashkent"),
        ("UTC+6 — Алматы", "Asia/Almaty"),
    ],
    2: [
        ("UTC+7 — Бангкок", "Asia/Bangkok"),
        ("UTC+8 — Пекин", "Asia/Shanghai"),
        ("UTC+9 — Токио", "Asia/Tokyo"),
        ("UTC+10 — Сидней", "Australia/Sydney"),
        ("UTC+11 — Нумеа", "Pacific/Noumea"),
        ("UTC+12 — Окленд", "Pacific/Auckland"),
        ("UTC+13 — Апиа", "Pacific/Apia"),
        ("UTC+14 — Киритимати", "Pacific/Kiritimati"),
    ],
    3: [
        ("UTC−12 — Бейкер-Айленд", "Etc/GMT+12"),
        ("UTC−11 — Паго-Паго", "Pacific/Pago_Pago"),
        ("UTC−10 — Гонолулу", "Pacific/Honolulu"),
        ("UTC−9 — Анкоридж", "America/Anchorage"),
        ("UTC−8 — Лос-Анджелес", "America/Los_Angeles"),
        ("UTC−7 — Денвер", "America/Denver"),
        ("UTC−6 — Чикаго", "America/Chicago"),
        ("UTC−5 — Нью-Йорк", "America/New_York"),
        ("UTC−4 — Каракас", "America/Caracas"),
        ("UTC−3 — Буэнос-Айрес", "America/Argentina/Buenos_Aires"),
        ("UTC−2 — Южная Георгия", "Atlantic/South_Georgia"),
    ],
}

MAX_TZ_PAGE = max(TZ_PAGES.keys())


def build_timezone_keyboard(
    page: int,
    prefix: str,
    include_manual: bool = True,
    include_cancel: bool = True,
) -> InlineKeyboardMarkup:
    page = max(1, min(page, MAX_TZ_PAGE))

    builder = InlineKeyboardBuilder()
    for button_text, iana_tz in TZ_PAGES[page]:
        builder.button(text=button_text, callback_data=f"{prefix}:set:{iana_tz}")
    builder.adjust(2)

    if page < MAX_TZ_PAGE:
        builder.row(InlineKeyboardButton(text="еще", callback_data=f"{prefix}:page:{page + 1}"))
    if include_manual:
        builder.row(InlineKeyboardButton(text="Ввести вручную", callback_data=f"{prefix}:manual"))
    if include_cancel:
        builder.row(InlineKeyboardButton(text="Отмена", callback_data=f"{prefix}:cancel"))
    return builder.as_markup()
