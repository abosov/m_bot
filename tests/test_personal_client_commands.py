import types
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

import pytest

from handlers.personal_bot.routers.client import commands as client_commands


class DummyMessage:
    def __init__(self, text: str, from_user=None):
        self.text = text
        self.from_user = from_user
        self.answers = []

    async def answer(self, text, **kwargs):
        self.answers.append((text, kwargs))


class DummyState:
    def __init__(self):
        self.state = None
        self.data = {}

    async def set_state(self, state):
        self.state = state

    async def update_data(self, **kwargs):
        self.data.update(kwargs)

    async def get_data(self):
        return dict(self.data)

    async def clear(self):
        self.state = None
        self.data = {}


class _AvailabilityByInterval:
    def __init__(self, by_start_hour: dict[int, list[datetime]]):
        self.by_start_hour = by_start_hour

    async def get_candidate_slots_for_date_range(self, **kwargs):
        start = kwargs["interval_start"]
        return self.by_start_hour.get(start.hour, [])


class _Result:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


def _mock_client_tz_session_factory(*, timezone_name: str | None):
    class _Session:
        async def execute(self, _stmt):
            if timezone_name is None:
                return _Result(None)
            return _Result(types.SimpleNamespace(client_timezone=timezone_name))

    class _Ctx:
        async def __aenter__(self):
            return _Session()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    return lambda: _Ctx()


@pytest.mark.asyncio
async def test_client_menu_buttons_return_stubs():
    book_msg = DummyMessage("Записаться")
    state = DummyState()

    async def _tz(_specialist_id):
        return ZoneInfo("UTC")

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(client_commands, "_get_specialist_tz", _tz)
    monkeypatch.setattr(
        client_commands,
        "_first_available_day",
        lambda **_kwargs: date(2026, 2, 20),
    )
    monkeypatch.setattr(
        client_commands,
        "async_session_factory",
        _mock_client_tz_session_factory(timezone_name=None),
    )

    await client_commands.client_book_button(book_msg, actor="client", state=state, specialist_id="sp-id")
    monkeypatch.undo()

    assert book_msg.answers[0][0] == "Выберите день (GMT+0):"
    assert book_msg.answers[0][1].get("reply_markup") is not None
    assert state.state == client_commands.ClientBookingState.waiting_for_day
    assert state.data["booking_available_days"] == [
        "2026-02-20",
        "2026-02-21",
        "2026-02-22",
        "2026-02-23",
        "2026-02-24",
        "2026-02-25",
        "2026-02-26",
    ]

    appts_msg = DummyMessage("Мои записи (пока stub)", from_user=types.SimpleNamespace(id=42))

    async def _render(*_args, **_kwargs):
        await appts_msg.answer("Мои записи скоро будет доступен")

    monkeypatch.setattr(client_commands, "_render_client_appointments", _render)
    await client_commands.client_my_appointments_button(appts_msg, actor="client", specialist_id="sp-id")
    assert "скоро будет доступен" in appts_msg.answers[0][0]
    monkeypatch.undo()

    tz_msg = DummyMessage("Сменить часовой пояс (пока stub)")
    await client_commands.client_change_timezone_button(tz_msg, actor="client")
    assert "скоро будет доступна" in tz_msg.answers[0][0]


def test_first_available_day_cutoff_rules():
    tz = ZoneInfo("Europe/Moscow")

    before_cutoff = datetime(2026, 2, 15, 17, 0, tzinfo=timezone.utc)
    assert client_commands._first_available_day(now_utc=before_cutoff, specialist_tz=tz) == date(2026, 2, 16)

    after_cutoff = datetime(2026, 2, 15, 19, 0, tzinfo=timezone.utc)
    assert client_commands._first_available_day(now_utc=after_cutoff, specialist_tz=tz) == date(2026, 2, 17)


@pytest.mark.asyncio
async def test_client_pick_day_shows_available_intervals(monkeypatch):
    state = DummyState()
    message = DummyMessage("")

    callback = types.SimpleNamespace(
        data="client_book_day:2026-02-21",
        message=message,
        from_user=types.SimpleNamespace(id=42),
        answers=[],
    )

    async def _callback_answer(*args, **kwargs):
        callback.answers.append((args, kwargs))

    callback.answer = _callback_answer

    row = types.SimpleNamespace(
        is_working=True,
        interval_1_start=time(9, 0),
        interval_1_end=time(12, 0),
        interval_2_start=None,
        interval_2_end=None,
        interval_3_start=time(18, 0),
        interval_3_end=time(21, 0),
    )
    async def _weekly(**_kwargs):
        return row

    async def _tz(_specialist_id):
        return ZoneInfo("UTC")

    async def _duration(_specialist_id):
        return 60

    monkeypatch.setattr(client_commands, "_get_weekly_availability_row", _weekly)
    monkeypatch.setattr(client_commands, "_get_specialist_tz", _tz)
    monkeypatch.setattr(client_commands, "_get_session_duration_min", _duration)
    monkeypatch.setattr(
        client_commands,
        "availability_service",
        _AvailabilityByInterval({9: [datetime(2026, 2, 21, 9, 0)], 18: [datetime(2026, 2, 21, 18, 0)]}),
    )
    monkeypatch.setattr(
        client_commands,
        "async_session_factory",
        _mock_client_tz_session_factory(timezone_name="UTC"),
    )

    await client_commands.client_pick_day(callback, state=state, specialist_id="sp-id")

    assert state.state == client_commands.ClientBookingState.waiting_for_interval
    assert state.data["booking_date"] == "2026-02-21"
    assert state.data["booking_interval_options"] == ["morning", "evening"]
    assert state.data["booking_interval_bounds"] == {"morning": {"start": "09:00", "end": "12:00"}, "evening": {"start": "18:00", "end": "21:00"}}
    assert message.answers[0][0] == "Выберите диапазон (GMT+0):"
    assert message.answers[0][1].get("reply_markup") is not None
    assert len(callback.answers) == 1


@pytest.mark.asyncio
async def test_client_pick_day_without_intervals_shows_empty_message(monkeypatch):
    state = DummyState()
    message = DummyMessage("")

    callback = types.SimpleNamespace(
        data="client_book_day:2026-02-21",
        message=message,
        from_user=types.SimpleNamespace(id=42),
        answers=[],
    )

    async def _callback_answer(*args, **kwargs):
        callback.answers.append((args, kwargs))

    callback.answer = _callback_answer

    row = types.SimpleNamespace(
        is_working=False,
        interval_1_start=None,
        interval_1_end=None,
        interval_2_start=None,
        interval_2_end=None,
        interval_3_start=None,
        interval_3_end=None,
    )
    async def _weekly(**_kwargs):
        return row

    async def _tz(_specialist_id):
        return ZoneInfo("UTC")

    async def _duration(_specialist_id):
        return 60

    monkeypatch.setattr(client_commands, "_get_weekly_availability_row", _weekly)
    monkeypatch.setattr(client_commands, "_get_specialist_tz", _tz)
    monkeypatch.setattr(client_commands, "_get_session_duration_min", _duration)
    monkeypatch.setattr(
        client_commands,
        "availability_service",
        _AvailabilityByInterval({9: [datetime(2026, 2, 21, 9, 0)], 18: [datetime(2026, 2, 21, 18, 0)]}),
    )
    monkeypatch.setattr(
        client_commands,
        "async_session_factory",
        _mock_client_tz_session_factory(timezone_name="UTC"),
    )

    await client_commands.client_pick_day(callback, state=state, specialist_id="sp-id")

    assert message.answers[0][0] == "На выбранный день нет доступных диапазонов."
    assert len(callback.answers) == 1


@pytest.mark.asyncio
async def test_client_pick_interval_shows_slots_as_buttons(monkeypatch):
    state = DummyState()
    state.data = {
        "booking_date": "2026-02-21",
        "booking_interval_options": ["morning", "day", "evening"],
        "booking_interval_bounds": {"day": {"start": "12:00", "end": "18:00"}},
    }
    message = DummyMessage("")

    callback = types.SimpleNamespace(
        data="client_book_interval:2026-02-21:day",
        message=message,
        from_user=types.SimpleNamespace(id=42),
        answers=[],
    )

    async def _callback_answer(*args, **kwargs):
        callback.answers.append((args, kwargs))

    callback.answer = _callback_answer

    class _Availability:
        async def get_candidate_slots_for_date_range(self, **kwargs):
            return [datetime(2026, 2, 21, 12, 0), datetime(2026, 2, 21, 12, 30)]

    async def _tz(_specialist_id):
        return ZoneInfo("UTC")

    monkeypatch.setattr(client_commands, "availability_service", _Availability())
    monkeypatch.setattr(client_commands, "_get_specialist_tz", _tz)
    monkeypatch.setattr(
        client_commands,
        "async_session_factory",
        _mock_client_tz_session_factory(timezone_name="UTC"),
    )

    await client_commands.client_pick_interval(callback, state=state, specialist_id="sp-id")

    assert message.answers[0][0] == "Выберите слот (GMT+0):"
    markup = message.answers[0][1].get("reply_markup")
    assert markup is not None
    assert len(markup.inline_keyboard) == 1
    assert [button.text for button in markup.inline_keyboard[0]] == ["12:00", "12:30"]
    assert len(callback.answers) == 1


@pytest.mark.asyncio
async def test_client_book_button_shows_gmt_in_header(monkeypatch):
    book_msg = DummyMessage("Записаться", from_user=types.SimpleNamespace(id=42))
    state = DummyState()

    async def _tz(_specialist_id):
        return ZoneInfo("UTC")

    monkeypatch.setattr(client_commands, "_get_specialist_tz", _tz)
    monkeypatch.setattr(client_commands, "_first_available_day", lambda **_kwargs: date(2026, 2, 20))
    monkeypatch.setattr(
        client_commands,
        "async_session_factory",
        _mock_client_tz_session_factory(timezone_name="Europe/Moscow"),
    )

    await client_commands.client_book_button(book_msg, actor="client", state=state, specialist_id="sp-id")

    assert book_msg.answers[0][0] == "Выберите день (GMT+3):"


@pytest.mark.asyncio
async def test_client_pick_day_shows_gmt_in_header(monkeypatch):
    state = DummyState()
    message = DummyMessage("")

    callback = types.SimpleNamespace(
        data="client_book_day:2026-02-21",
        message=message,
        from_user=types.SimpleNamespace(id=42),
        answers=[],
    )

    async def _callback_answer(*args, **kwargs):
        callback.answers.append((args, kwargs))

    callback.answer = _callback_answer

    row = types.SimpleNamespace(
        is_working=True,
        interval_1_start=time(9, 0),
        interval_1_end=time(12, 0),
        interval_2_start=None,
        interval_2_end=None,
        interval_3_start=time(18, 0),
        interval_3_end=time(21, 0),
    )

    async def _weekly(**_kwargs):
        return row

    async def _tz(_specialist_id):
        return ZoneInfo("UTC")

    async def _duration(_specialist_id):
        return 60

    monkeypatch.setattr(client_commands, "_get_weekly_availability_row", _weekly)
    monkeypatch.setattr(client_commands, "_get_specialist_tz", _tz)
    monkeypatch.setattr(client_commands, "_get_session_duration_min", _duration)
    monkeypatch.setattr(
        client_commands,
        "availability_service",
        _AvailabilityByInterval({9: [datetime(2026, 2, 21, 9, 0)], 18: [datetime(2026, 2, 21, 18, 0)]}),
    )
    monkeypatch.setattr(
        client_commands,
        "async_session_factory",
        _mock_client_tz_session_factory(timezone_name="Europe/Moscow"),
    )

    await client_commands.client_pick_day(callback, state=state, specialist_id="sp-id")

    assert message.answers[0][0] == "Выберите диапазон (GMT+3):"


@pytest.mark.asyncio
async def test_client_pick_interval_shows_gmt_in_header(monkeypatch):
    state = DummyState()
    state.data = {
        "booking_date": "2026-02-21",
        "booking_interval_options": ["morning", "day", "evening"],
        "booking_interval_bounds": {"day": {"start": "12:00", "end": "18:00"}},
    }
    message = DummyMessage("")

    callback = types.SimpleNamespace(
        data="client_book_interval:2026-02-21:day",
        message=message,
        from_user=types.SimpleNamespace(id=42),
        answers=[],
    )

    async def _callback_answer(*args, **kwargs):
        callback.answers.append((args, kwargs))

    callback.answer = _callback_answer

    class _Availability:
        async def get_candidate_slots_for_date_range(self, **kwargs):
            return [datetime(2026, 2, 21, 12, 0), datetime(2026, 2, 21, 12, 30)]

    async def _tz(_specialist_id):
        return ZoneInfo("UTC")

    monkeypatch.setattr(client_commands, "availability_service", _Availability())
    monkeypatch.setattr(client_commands, "_get_specialist_tz", _tz)
    monkeypatch.setattr(
        client_commands,
        "async_session_factory",
        _mock_client_tz_session_factory(timezone_name="Europe/Moscow"),
    )

    await client_commands.client_pick_interval(callback, state=state, specialist_id="sp-id")

    assert message.answers[0][0] == "Выберите слот (GMT+3):"


@pytest.mark.asyncio
async def test_client_pick_slot_creates_confirmed_appointment_and_returns_menu(monkeypatch):
    state = DummyState()
    message = DummyMessage("")

    callback = types.SimpleNamespace(
        data="client_book_slot:2026-02-21T12:00:00",
        message=message,
        from_user=types.SimpleNamespace(id=42),
        answers=[],
    )

    async def _callback_answer(*args, **kwargs):
        callback.answers.append((args, kwargs))

    callback.answer = _callback_answer

    class _Result:
        @staticmethod
        def scalar_one_or_none():
            return types.SimpleNamespace(client_id="cl-1")

    class _Session:
        def __init__(self):
            self.added = []
            self.commits = 0

        async def execute(self, _stmt):
            return _Result()

        async def get(self, model, _pk):
            if model is client_commands.SpecialistProfile:
                return types.SimpleNamespace(session_duration_min=45, specialist_timezone="UTC")
            if model is client_commands.SpecialistCalendarSettings:
                return None
            return None

        def add(self, obj):
            self.added.append(obj)

        async def commit(self):
            self.commits += 1

    session = _Session()

    class _Ctx:
        async def __aenter__(self):
            return session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    async def _tz(_specialist_id):
        return ZoneInfo("UTC")

    monkeypatch.setattr(client_commands, "async_session_factory", lambda: _Ctx())
    monkeypatch.setattr(client_commands, "_get_specialist_tz", _tz)

    await client_commands.client_pick_slot(callback, state=state, specialist_id="sp-id")

    assert session.commits == 1
    assert len(session.added) == 1
    appointment = session.added[0]
    assert appointment.booking_state == client_commands.BookingState.confirmed
    assert appointment.start_at_utc == datetime(2026, 2, 21, 12, 0, tzinfo=timezone.utc)
    assert appointment.end_at_utc == datetime(2026, 2, 21, 12, 45, tzinfo=timezone.utc)
    assert appointment.gcal_event_id is None
    assert message.answers[0][0] == "Запись создана"
    assert message.answers[0][1].get("reply_markup") is not None
    assert len(callback.answers) == 1


@pytest.mark.asyncio
async def test_client_pick_slot_logs_google_error_and_keeps_confirmed(monkeypatch):
    state = DummyState()
    message = DummyMessage("")

    callback = types.SimpleNamespace(
        data="client_book_slot:2026-02-21T12:00:00",
        message=message,
        from_user=types.SimpleNamespace(id=42),
        answers=[],
    )

    async def _callback_answer(*args, **kwargs):
        callback.answers.append((args, kwargs))

    callback.answer = _callback_answer

    class _Result:
        @staticmethod
        def scalar_one_or_none():
            return types.SimpleNamespace(
                client_id="cl-1",
                display_name="Анна",
                tg_username="anna",
                tg_user_id=42,
                client_code="CL-42",
            )

    class _Session:
        def __init__(self):
            self.added = []
            self.commits = 0

        async def execute(self, _stmt):
            return _Result()

        async def get(self, model, _pk):
            if model is client_commands.SpecialistProfile:
                return types.SimpleNamespace(session_duration_min=45, specialist_timezone="UTC")
            if model is client_commands.SpecialistCalendarSettings:
                return types.SimpleNamespace(calendar_id="cal-1")
            return None

        def add(self, obj):
            self.added.append(obj)

        async def commit(self):
            self.commits += 1

    session = _Session()

    class _Ctx:
        async def __aenter__(self):
            return session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    async def _tz(_specialist_id):
        return ZoneInfo("UTC")

    async def _raise_google_error(
        *,
        specialist_id,
        calendar_id,
        start_at_utc,
        end_at_utc,
        specialist_tz,
        client_display_name,
        client_tg_username=None,
        client_tg_user_id=None,
        client_code=None,
    ):
        raise RuntimeError("google down")

    logged = {"called": False}

    def _logger_exception(*_args, **_kwargs):
        logged["called"] = True

    monkeypatch.setattr(client_commands, "async_session_factory", lambda: _Ctx())
    monkeypatch.setattr(client_commands, "_get_specialist_tz", _tz)
    monkeypatch.setattr(client_commands, "create_appointment_event", _raise_google_error)
    monkeypatch.setattr(client_commands.logger, "exception", _logger_exception)

    await client_commands.client_pick_slot(callback, state=state, specialist_id="sp-id")

    assert session.commits == 1
    appointment = session.added[0]
    assert appointment.booking_state == client_commands.BookingState.confirmed
    assert appointment.gcal_event_id is None
    assert logged["called"] is True


@pytest.mark.asyncio
async def test_client_pick_slot_passes_client_tg_user_id_and_client_code_to_google_event(monkeypatch):
    state = DummyState()
    message = DummyMessage("")

    callback = types.SimpleNamespace(
        data="client_book_slot:2026-02-21T12:00:00",
        message=message,
        from_user=types.SimpleNamespace(id=42),
        answers=[],
    )

    async def _callback_answer(*args, **kwargs):
        callback.answers.append((args, kwargs))

    callback.answer = _callback_answer

    class _Result:
        @staticmethod
        def scalar_one_or_none():
            return types.SimpleNamespace(
                client_id="cl-1",
                display_name="Анна",
                tg_username="anna",
                tg_user_id=42,
                client_code="CL-42",
            )

    class _Session:
        def __init__(self):
            self.added = []
            self.commits = 0

        async def execute(self, _stmt):
            return _Result()

        async def get(self, model, _pk):
            if model is client_commands.SpecialistProfile:
                return types.SimpleNamespace(session_duration_min=45, specialist_timezone="UTC")
            if model is client_commands.SpecialistCalendarSettings:
                return types.SimpleNamespace(calendar_id="cal-1")
            return None

        def add(self, obj):
            self.added.append(obj)

        async def commit(self):
            self.commits += 1

    session = _Session()

    class _Ctx:
        async def __aenter__(self):
            return session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    async def _tz(_specialist_id):
        return ZoneInfo("UTC")

    captured_kwargs = {}

    async def _create_event_stub(**kwargs):
        captured_kwargs.update(kwargs)
        return {"id": "evt-1"}

    monkeypatch.setattr(client_commands, "async_session_factory", lambda: _Ctx())
    monkeypatch.setattr(client_commands, "_get_specialist_tz", _tz)
    monkeypatch.setattr(client_commands, "create_appointment_event", _create_event_stub)

    await client_commands.client_pick_slot(callback, state=state, specialist_id="sp-id")

    assert captured_kwargs["client_tg_user_id"] == 42
    assert captured_kwargs["client_code"] == "CL-42"


@pytest.mark.asyncio
async def test_client_capture_display_name_saves_name_and_shows_menu(monkeypatch):
    message = DummyMessage("Анна", from_user=types.SimpleNamespace(id=42))
    client = types.SimpleNamespace(display_name=None)

    class _Result:
        @staticmethod
        def scalar_one_or_none():
            return client

    class _Session:
        def __init__(self):
            self.committed = False

        async def execute(self, _stmt):
            return _Result()

        async def commit(self):
            self.committed = True

    session = _Session()

    class _Ctx:
        async def __aenter__(self):
            return session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(client_commands, "async_session_factory", lambda: _Ctx())

    await client_commands.client_capture_display_name(message, actor="client", specialist_id="sp-id")

    assert client.display_name == "Анна"
    assert session.committed is True
    assert "Приятно познакомиться" in message.answers[0][0]
    assert message.answers[0][1].get("reply_markup") is not None


@pytest.mark.asyncio
async def test_client_pick_day_marks_empty_interval_as_noop_button(monkeypatch):
    state = DummyState()
    message = DummyMessage("")

    callback = types.SimpleNamespace(
        data="client_book_day:2026-02-21",
        message=message,
        from_user=types.SimpleNamespace(id=42),
        answers=[],
    )

    async def _callback_answer(*args, **kwargs):
        callback.answers.append((args, kwargs))

    callback.answer = _callback_answer

    row = types.SimpleNamespace(
        is_working=True,
        interval_1_start=time(9, 0),
        interval_1_end=time(12, 0),
        interval_2_start=None,
        interval_2_end=None,
        interval_3_start=time(18, 0),
        interval_3_end=time(21, 0),
    )

    async def _weekly(**_kwargs):
        return row

    async def _tz(_specialist_id):
        return ZoneInfo("UTC")

    async def _duration(_specialist_id):
        return 60

    monkeypatch.setattr(client_commands, "_get_weekly_availability_row", _weekly)
    monkeypatch.setattr(client_commands, "_get_specialist_tz", _tz)
    monkeypatch.setattr(client_commands, "_get_session_duration_min", _duration)
    monkeypatch.setattr(
        client_commands,
        "availability_service",
        _AvailabilityByInterval({9: [], 18: [datetime(2026, 2, 21, 18, 0)]}),
    )
    monkeypatch.setattr(
        client_commands,
        "async_session_factory",
        _mock_client_tz_session_factory(timezone_name="UTC"),
    )

    await client_commands.client_pick_day(callback, state=state, specialist_id="sp-id")

    markup = message.answers[0][1].get("reply_markup")
    assert markup is not None
    buttons = [button for row in markup.inline_keyboard for button in row]
    assert buttons[0].callback_data == "noop"
    assert buttons[1].callback_data == "client_book_interval:2026-02-21:evening"


@pytest.mark.asyncio
async def test_noop_callback_answers():
    callback = types.SimpleNamespace(answers=[])

    async def _callback_answer(*args, **kwargs):
        callback.answers.append((args, kwargs))

    callback.answer = _callback_answer

    await client_commands.noop_callback(callback)

    assert len(callback.answers) == 1
