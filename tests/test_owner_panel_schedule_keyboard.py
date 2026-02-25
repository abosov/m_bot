from handlers.personal_bot.routers.specialist.owner_panel import build_weekday_button_text


def test_build_weekday_button_text_marks_only_working_days():
    working_days = {0, 2, 4}

    assert build_weekday_button_text(0, working_days) == "✅ Пн"
    assert build_weekday_button_text(1, working_days) == "Вт"
    assert build_weekday_button_text(2, working_days) == "✅ Ср"
    assert build_weekday_button_text(3, working_days) == "Чт"
    assert build_weekday_button_text(4, working_days) == "✅ Пт"
    assert build_weekday_button_text(5, working_days) == "Сб"
    assert build_weekday_button_text(6, working_days) == "Вс"

import pytest

from handlers.personal_bot.routers.specialist import owner_panel


def test_schedule_intervals_keyboard_has_expected_order():
    keyboard = owner_panel._schedule_intervals_keyboard()
    rows = keyboard.inline_keyboard

    assert rows[0][0].text == "Интервал 1"
    assert rows[1][0].text == "Интервал 2"
    assert rows[2][0].text == "Интервал 3"
    assert rows[3][0].text == "⬅️ Назад"
    assert rows[3][0].callback_data == "schedule:back_to_weekdays"


def test_schedule_weekday_keyboard_has_intervals_shortcut():
    keyboard = owner_panel._schedule_weekday_keyboard({0, 2, 4})
    rows = keyboard.inline_keyboard

    assert rows[4][0].text == "🕒 Интервалы"
    assert rows[4][0].callback_data == "schedule:intervals_menu"


@pytest.mark.asyncio
async def test_render_intervals_menu_uses_repo_values_and_ensure(monkeypatch):
    calls = {"ensured": 0}

    async def _ensure(_specialist_id):
        calls["ensured"] += 1
        return False

    class _Repo:
        async def get_working_intervals(self, _specialist_id):
            return {
                1: (540, 720),
                2: (None, None),
                3: (1020, 1260),
            }

    class _Message:
        def __init__(self):
            self.text = None
            self.reply_markup = None

        async def edit_text(self, text, reply_markup):
            self.text = text
            self.reply_markup = reply_markup
            return self

    async def _required(_specialist_id):
        return 60

    monkeypatch.setattr(owner_panel, "ensure_default_working_intervals", _ensure)
    monkeypatch.setattr(owner_panel, "WorkingIntervalsRepository", lambda: _Repo())
    monkeypatch.setattr(owner_panel, "_get_required_interval_min", _required)

    message = _Message()
    await owner_panel._render_intervals_menu(message, specialist_id="sid")

    assert calls["ensured"] == 1
    assert "Интервал 1: 09:00–12:00" in message.text
    assert "Интервал 2: —" in message.text
    assert "Интервал 3: 17:00–21:00" in message.text
    assert message.reply_markup.inline_keyboard[0][0].text == "Интервал 1"


@pytest.mark.asyncio
async def test_owner_panel_change_schedule_opens_weekday_picker(monkeypatch):
    captured = {"state": None, "remembered": 0, "answered": 0, "rendered_for": None}

    class _State:
        async def set_state(self, value):
            captured["state"] = value

    class _Message:
        pass

    class _Callback:
        def __init__(self):
            self.message = _Message()

        async def answer(self):
            captured["answered"] += 1

    async def _remember(_state, _message):
        captured["remembered"] += 1

    async def _render(_callback, *, specialist_id):
        captured["rendered_for"] = specialist_id

    monkeypatch.setattr(owner_panel, "_remember_nav_message", _remember)
    monkeypatch.setattr(owner_panel, "_render_weekday_picker", _render)

    await owner_panel.owner_panel_change_schedule(
        callback=_Callback(),
        state=_State(),
        specialist_id="sid",
    )

    assert captured["state"] == owner_panel.ScheduleEditStates.choosing_weekday
    assert captured["remembered"] == 1
    assert captured["answered"] == 1
    assert captured["rendered_for"] == "sid"


@pytest.mark.asyncio
async def test_owner_panel_change_schedule_renders_weekdays_not_intervals(monkeypatch):
    class _State:
        async def set_state(self, _value):
            return None

    class _Message:
        def __init__(self):
            self.edits = []

        async def edit_text(self, text, reply_markup):
            self.edits.append((text, reply_markup))
            return self

    class _Callback:
        def __init__(self):
            self.message = _Message()

        async def answer(self):
            return None

    async def _remember(_state, _message):
        return None

    async def _days(_specialist_id):
        return {0, 2, 4}

    monkeypatch.setattr(owner_panel, "_remember_nav_message", _remember)
    monkeypatch.setattr(owner_panel, "get_working_days", _days)

    callback = _Callback()
    await owner_panel.owner_panel_change_schedule(
        callback=callback,
        state=_State(),
        specialist_id="sid",
    )

    assert len(callback.message.edits) == 1
    text, reply_markup = callback.message.edits[0]
    assert "Выберите рабочие дни недели" in text
    assert "Выберите интервал" not in text
    assert reply_markup.inline_keyboard[4][0].callback_data == "schedule:intervals_menu"






@pytest.mark.asyncio
async def test_schedule_back_to_weekdays_returns_weekday_picker(monkeypatch):
    captured = {"state": None, "answered": 0, "rendered_for": None}

    class _State:
        async def set_state(self, value):
            captured["state"] = value

    class _Message:
        pass

    class _Callback:
        def __init__(self):
            self.message = _Message()

        async def answer(self):
            captured["answered"] += 1

    async def _render(_callback, *, specialist_id):
        captured["rendered_for"] = specialist_id

    monkeypatch.setattr(owner_panel, "_render_weekday_picker", _render)

    await owner_panel.schedule_back_to_weekdays(
        callback=_Callback(),
        state=_State(),
        specialist_id="sid",
    )

    assert captured["state"] == owner_panel.ScheduleEditStates.choosing_weekday
    assert captured["answered"] == 1
    assert captured["rendered_for"] == "sid"


@pytest.mark.asyncio
async def test_schedule_interval_select_sets_state_and_renders_actions(monkeypatch):
    captured = {"data": None, "state": None, "answered": 0, "render": None}

    class _State:
        async def update_data(self, **kwargs):
            captured["data"] = kwargs

        async def set_state(self, value):
            captured["state"] = value

    class _Message:
        pass

    class _Callback:
        data = "schedule:interval:1"

        def __init__(self):
            self.message = _Message()

        async def answer(self):
            captured["answered"] += 1

    async def _render(message, specialist_id, idx):
        captured["render"] = (message, specialist_id, idx)

    monkeypatch.setattr(owner_panel, "_render_interval_actions_menu", _render)

    callback = _Callback()
    await owner_panel.schedule_interval_select(callback=callback, state=_State(), specialist_id="sid")

    assert captured["data"] == {"schedule_interval_idx": 1}
    assert captured["state"] == owner_panel.ScheduleEditStates.interval_menu
    assert captured["answered"] == 1
    assert captured["render"] == (callback.message, "sid", 1)


@pytest.mark.asyncio
async def test_schedule_interval_select_renders_interval_actions_text(monkeypatch):
    class _State:
        async def update_data(self, **_kwargs):
            return None

        async def set_state(self, _value):
            return None

    class _Message:
        def __init__(self):
            self.edits = []

        async def edit_text(self, text, reply_markup):
            self.edits.append((text, reply_markup))
            return self

    class _Callback:
        data = "schedule:interval:1"

        def __init__(self):
            self.message = _Message()

        async def answer(self, *_args, **_kwargs):
            return None

    async def _ensure(_specialist_id):
        return False

    class _Repo:
        async def get_working_intervals(self, _specialist_id):
            return {1: (540, 720), 2: (780, 1020), 3: (None, None)}

    monkeypatch.setattr(owner_panel, "ensure_default_working_intervals", _ensure)
    monkeypatch.setattr(owner_panel, "WorkingIntervalsRepository", lambda: _Repo())

    callback = _Callback()
    await owner_panel.schedule_interval_select(
        callback=callback,
        state=_State(),
        specialist_id="sid",
    )

    assert len(callback.message.edits) == 1
    text, reply_markup = callback.message.edits[0]
    assert "Интервал 1: 09:00–12:00" in text
    assert "Выберите действие" in text
    assert reply_markup.inline_keyboard[0][0].text == "Изменить начало"


def test_schedule_interval_actions_keyboard_has_expected_order():
    keyboard = owner_panel._schedule_interval_actions_keyboard(2)
    rows = keyboard.inline_keyboard

    assert rows[0][0].text == "Изменить начало"
    assert rows[1][0].text == "Изменить конец"
    assert rows[2][0].text == "Выключить интервал"
    assert rows[3][0].text == "⬅️ Назад"
    assert rows[3][0].callback_data == "schedule:intervals_menu"


@pytest.mark.asyncio
async def test_render_interval_actions_menu_edits_current_message(monkeypatch):
    async def _ensure(_specialist_id):
        return False

    class _Repo:
        async def get_working_intervals(self, _specialist_id):
            return {1: (540, 720), 2: (780, 1020), 3: (None, None)}

    class _Message:
        def __init__(self):
            self.edit_calls = []

        async def edit_text(self, text, reply_markup):
            self.edit_calls.append((text, reply_markup))
            return self

    monkeypatch.setattr(owner_panel, "ensure_default_working_intervals", _ensure)
    monkeypatch.setattr(owner_panel, "WorkingIntervalsRepository", lambda: _Repo())

    message = _Message()
    await owner_panel._render_interval_actions_menu(message, specialist_id="sid", idx=2)

    assert len(message.edit_calls) == 1
    text, reply_markup = message.edit_calls[0]
    assert "Интервал 2: 13:00–17:00" in text
    assert reply_markup.inline_keyboard[0][0].text == "Изменить начало"


def test_build_overlap_note_for_disabled_neighbor():
    note = owner_panel._build_overlap_note(
        before={1: (540, 720), 2: (780, 1020), 3: (1020, 1260)},
        after={1: (540, 1200), 2: (None, None), 3: (1200, 1260)},
        edited_idx=1,
    )

    assert note == "ℹ️ Интервал 2 выключен из-за перекрытия после изменения интервала 1."


def test_intervals_overview_text_contains_note():
    text = owner_panel._intervals_overview_text(
        {1: (540, 720), 2: (None, None), 3: (1020, 1260)},
        required_min=60,
        note="ℹ️ Причина",
    )

    assert "Интервал 1: 09:00–12:00" in text
    assert "Интервал 2: —" in text
    assert text.endswith("ℹ️ Причина")


def test_intervals_overview_text_marks_too_short_interval():
    text = owner_panel._intervals_overview_text(
        {
            1: (540, 560),
            2: (780, 1020),
            3: (None, None),
        },
        required_min=60,
    )

    assert "Интервал 1: 09:00–09:20" in text
    assert "⚠️ Слоты недоступны: окно короче 60 мин" in text
