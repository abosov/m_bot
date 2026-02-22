import asyncio

from calendar_bot.schedule_setup import (
    DAY_BACK_CALLBACK,
    DAY_TOGGLE_PREFIX,
    ScheduleSetupState,
    build_schedule_day_keyboard,
    handle_toggle_weekday,
    initialize_schedule_state,
)


class FakeRepo:
    async def get_working_days(self, specialist_id: int):
        assert specialist_id == 99
        return [0, 2, 6]


class FakeApi:
    def __init__(self):
        self.calls = []

    async def edit_message_reply_markup(self, *, chat_id, message_id, reply_markup):
        self.calls.append(
            {
                "chat_id": chat_id,
                "message_id": message_id,
                "reply_markup": reply_markup,
            }
        )


def test_initialize_schedule_state_loads_days_from_repo():
    state = ScheduleSetupState()
    asyncio.run(
        initialize_schedule_state(specialist_id=99, repository=FakeRepo(), state=state)
    )

    assert state.selected_weekdays == {0, 2, 6}


def test_toggle_changes_state_and_edits_markup():
    state = ScheduleSetupState(selected_weekdays={0})
    api = FakeApi()

    asyncio.run(
        handle_toggle_weekday(
            callback_data=f"{DAY_TOGGLE_PREFIX}:1",
            chat_id=111,
            message_id=222,
            state=state,
            api=api,
        )
    )

    assert state.selected_weekdays == {0, 1}
    assert len(api.calls) == 1

    markup = api.calls[0]["reply_markup"]
    monday_button = markup.inline_keyboard[0][0]
    tuesday_button = markup.inline_keyboard[0][1]

    assert monday_button.text == "Пн ✅"
    assert tuesday_button.text == "Вт ✅"


def test_toggle_off_removes_checkmark():
    state = ScheduleSetupState(selected_weekdays={0})
    api = FakeApi()

    asyncio.run(
        handle_toggle_weekday(
            callback_data=f"{DAY_TOGGLE_PREFIX}:0",
            chat_id=111,
            message_id=222,
            state=state,
            api=api,
        )
    )

    assert state.selected_weekdays == set()
    monday_button = api.calls[0]["reply_markup"].inline_keyboard[0][0]
    assert monday_button.text == "Пн"


def test_keyboard_has_expected_callback_data_and_back_button():
    markup = build_schedule_day_keyboard({6})

    sunday = markup.inline_keyboard[3][0]
    back = markup.inline_keyboard[4][0]

    assert sunday.callback_data == f"{DAY_TOGGLE_PREFIX}:6"
    assert sunday.text == "Вс ✅"
    assert back.callback_data == DAY_BACK_CALLBACK
    assert back.text == "Назад"
