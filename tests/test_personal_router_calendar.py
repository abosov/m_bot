import pytest

from handlers.personal_bot import router as personal_root_router
from handlers.personal_bot.routers.common import calendar as calendar_router


def _collect_router_names(router):
    names = [router.name]
    for sub in router.sub_routers:
        names.extend(_collect_router_names(sub))
    return names


def test_personal_root_router_includes_calendar_router():
    names = _collect_router_names(personal_root_router)
    assert "personal_bot_common_calendar" in names


@pytest.mark.asyncio
async def test_calendar_switch_stub_redirects_to_select(monkeypatch):
    called = {"value": False}

    class _State:
        async def get_state(self):
            return None

    class _User:
        id = 777

    class _Callback:
        from_user = _User()

    async def _select_stub(callback, state):
        called["value"] = True

    async def _specialist_stub(_tg_user_id):
        return 1

    monkeypatch.setattr(calendar_router, "_calendar_select", _select_stub)
    monkeypatch.setattr(calendar_router, "_get_specialist_id_by_tg_user_id", _specialist_stub)
    monkeypatch.setattr(calendar_router, "_log_personal_handler", lambda **kwargs: None)

    await calendar_router.personal_calendar_switch_stub(callback=_Callback(), state=_State())

    assert called["value"] is True


@pytest.mark.asyncio
async def test_personal_calendar_cancel_select_returns_to_onboarding(monkeypatch):
    called = {"render": False}

    class _State:
        def __init__(self):
            self.cleared = False

        async def get_state(self):
            return None

        async def clear(self):
            self.cleared = True

    class _User:
        id = 777

    class _Message:
        async def answer(self, _text):
            raise AssertionError("answer should not be called when specialist exists")

    class _Callback:
        from_user = _User()
        message = _Message()

        async def answer(self):
            return None

    async def _specialist_stub(_tg_user_id):
        return 1

    async def _render_stub(message, specialist_id):
        called["render"] = (specialist_id == 1)

    monkeypatch.setattr(calendar_router, "_log_personal_handler", lambda **kwargs: None)
    monkeypatch.setattr(calendar_router, "_get_specialist_id_by_tg_user_id", _specialist_stub)
    monkeypatch.setattr(calendar_router, "_render_onboarding_screen", _render_stub)

    state = _State()
    await calendar_router.personal_calendar_cancel_select(callback=_Callback(), state=state)

    assert state.cleared is True
    assert called["render"] is True


@pytest.mark.asyncio
async def test_personal_calendar_pick_success_sends_confirmation_and_answers(monkeypatch):
    rendered = {"value": False}

    class _State:
        def __init__(self):
            self.cleared = False

        async def get_state(self):
            return None

        async def get_data(self):
            return {"items": [{"id": "cal-1", "summary": "Alex psy", "timeZone": "UTC", "readOnly": False}]}

        async def clear(self):
            self.cleared = True

    class _User:
        id = 777

    class _Message:
        def __init__(self):
            self.answers = []

        async def answer(self, text):
            self.answers.append(text)

    class _Callback:
        def __init__(self):
            self.from_user = _User()
            self.data = "calendar:pick:0"
            self.message = _Message()
            self.answered = 0

        async def answer(self, *args, **kwargs):
            self.answered += 1

    class _Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def commit(self):
            return None

    async def _specialist_stub(_tg_user_id):
        return 1

    async def _test_event_stub(*args, **kwargs):
        return None

    async def _upsert_stub(**kwargs):
        return None

    async def _defaults_stub(session, specialist_id, preferred_timezone):
        return None

    async def _render_stub(message, specialist_id):
        rendered["value"] = specialist_id == 1

    monkeypatch.setattr(calendar_router, "_log_personal_handler", lambda **kwargs: None)
    monkeypatch.setattr(calendar_router, "_get_specialist_id_by_tg_user_id", _specialist_stub)
    monkeypatch.setattr(calendar_router, "create_and_cleanup_test_event", _test_event_stub)
    monkeypatch.setattr(calendar_router, "_upsert_calendar_settings", _upsert_stub)
    monkeypatch.setattr(calendar_router, "apply_specialist_defaults_if_missing", _defaults_stub)
    monkeypatch.setattr(calendar_router, "async_session_factory", lambda: _Session())
    monkeypatch.setattr(calendar_router, "_render_onboarding_screen", _render_stub)

    state = _State()
    callback = _Callback()
    await calendar_router.personal_calendar_pick(callback=callback, state=state)

    assert state.cleared is True
    assert callback.message.answers[0] == "Календарь применён."
    assert rendered["value"] is True
    assert callback.answered == 1


@pytest.mark.asyncio
async def test_personal_calendar_pick_failure_sends_error_and_answers(monkeypatch):
    class _State:
        async def get_state(self):
            return None

        async def get_data(self):
            return {"items": [{"id": "cal-1", "summary": "Alex B", "timeZone": "UTC", "readOnly": False}]}

    class _User:
        id = 777

    class _Message:
        def __init__(self):
            self.answers = []

        async def answer(self, text):
            self.answers.append(text)

    class _Callback:
        def __init__(self):
            self.from_user = _User()
            self.data = "calendar:pick:0"
            self.message = _Message()
            self.answered = 0

        async def answer(self, *args, **kwargs):
            self.answered += 1

    async def _specialist_stub(_tg_user_id):
        return 1

    async def _upsert_fails(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(calendar_router, "_log_personal_handler", lambda **kwargs: None)
    monkeypatch.setattr(calendar_router, "_get_specialist_id_by_tg_user_id", _specialist_stub)
    monkeypatch.setattr(calendar_router, "_upsert_calendar_settings", _upsert_fails)

    callback = _Callback()
    await calendar_router.personal_calendar_pick(callback=callback, state=_State())

    assert callback.message.answers[-1] == "Не удалось применить выбранный календарь. Попробуйте снова или нажмите «Обновить список»."
    assert callback.answered == 1


@pytest.mark.asyncio
async def test_personal_calendar_smoke_unexpected_error_answers_and_reports(monkeypatch):
    class _State:
        async def get_state(self):
            return None

    class _User:
        id = 777

    class _Message:
        def __init__(self):
            self.answers = []

        async def answer(self, text):
            self.answers.append(text)

    class _Callback:
        def __init__(self):
            self.from_user = _User()
            self.message = _Message()
            self.answered = 0

        async def answer(self, *args, **kwargs):
            self.answered += 1

    class _BadSession:
        async def __aenter__(self):
            raise RuntimeError("db down")

        async def __aexit__(self, exc_type, exc, tb):
            return False

    async def _specialist_stub(_tg_user_id):
        return 1

    async def _notify_stub(**kwargs):
        return None

    monkeypatch.setattr(calendar_router, "_log_personal_handler", lambda **kwargs: None)
    monkeypatch.setattr(calendar_router, "_get_specialist_id_by_tg_user_id", _specialist_stub)
    monkeypatch.setattr(calendar_router, "async_session_factory", lambda: _BadSession())
    monkeypatch.setattr(calendar_router, "notify_exception", _notify_stub)

    callback = _Callback()
    await calendar_router.personal_calendar_smoke(callback=callback, state=_State())

    assert callback.message.answers[-1] == "⚠️ Не удалось проверить интеграцию. Попробуйте снова позже."
    assert callback.answered == 1
