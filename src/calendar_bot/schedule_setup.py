from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Protocol

WEEKDAY_LABELS: dict[int, str] = {
    0: "Пн",
    1: "Вт",
    2: "Ср",
    3: "Чт",
    4: "Пт",
    5: "Сб",
    6: "Вс",
}

DAY_TOGGLE_PREFIX = "schedule_day_toggle"
DAY_BACK_CALLBACK = "schedule_day_back"


@dataclass
class InlineButton:
    text: str
    callback_data: str


@dataclass
class InlineKeyboardMarkup:
    inline_keyboard: list[list[InlineButton]]


@dataclass
class ScheduleSetupState:
    selected_weekdays: set[int] = field(default_factory=set)


class TelegramApi(Protocol):
    async def edit_message_reply_markup(
        self, *, chat_id: int, message_id: int, reply_markup: InlineKeyboardMarkup
    ) -> None: ...


class SpecialistProfileRepository(Protocol):
    async def get_working_days(self, specialist_id: int) -> Iterable[int]: ...


def normalize_weekdays(days: Iterable[int]) -> set[int]:
    return {int(day) for day in days if int(day) in WEEKDAY_LABELS}


def build_schedule_day_keyboard(selected_weekdays: set[int]) -> InlineKeyboardMarkup:
    def day_label(weekday: int) -> str:
        base = WEEKDAY_LABELS[weekday]
        return f"{base} ✅" if weekday in selected_weekdays else base

    keyboard = [
        [
            InlineButton(day_label(0), f"{DAY_TOGGLE_PREFIX}:0"),
            InlineButton(day_label(1), f"{DAY_TOGGLE_PREFIX}:1"),
        ],
        [
            InlineButton(day_label(2), f"{DAY_TOGGLE_PREFIX}:2"),
            InlineButton(day_label(3), f"{DAY_TOGGLE_PREFIX}:3"),
        ],
        [
            InlineButton(day_label(4), f"{DAY_TOGGLE_PREFIX}:4"),
            InlineButton(day_label(5), f"{DAY_TOGGLE_PREFIX}:5"),
        ],
        [InlineButton(day_label(6), f"{DAY_TOGGLE_PREFIX}:6")],
        [InlineButton("Назад", DAY_BACK_CALLBACK)],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


async def initialize_schedule_state(
    *,
    specialist_id: int,
    repository: SpecialistProfileRepository,
    state: ScheduleSetupState,
) -> None:
    state.selected_weekdays = normalize_weekdays(
        await repository.get_working_days(specialist_id)
    )


async def handle_toggle_weekday(
    *,
    callback_data: str,
    chat_id: int,
    message_id: int,
    state: ScheduleSetupState,
    api: TelegramApi,
) -> None:
    _, weekday_raw = callback_data.split(":", maxsplit=1)
    weekday = int(weekday_raw)

    if weekday not in WEEKDAY_LABELS:
        return

    if weekday in state.selected_weekdays:
        state.selected_weekdays.remove(weekday)
    else:
        state.selected_weekdays.add(weekday)

    await api.edit_message_reply_markup(
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=build_schedule_day_keyboard(state.selected_weekdays),
    )
