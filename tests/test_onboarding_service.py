import os

os.environ.setdefault("APP_ENV", "local")
os.environ.setdefault("MASTER_BOT_TOKEN", "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi")
os.environ.setdefault("ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")

import types
import uuid

import pytest

from database import SpecialistStatus
from services import onboarding


class DummySessionCtx:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class DummyScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


@pytest.mark.asyncio
async def test_is_specialist_ready_requires_calendar_smoke_ok(monkeypatch):
    specialist_id = uuid.uuid4()

    class Session:
        def __init__(self):
            self.calls = 0

        async def execute(self, _query):
            self.calls += 1
            # profile exists, active bot exists, calendar smoke missing
            values = [specialist_id, specialist_id, None]
            return DummyScalarResult(values[self.calls - 1])

    session = Session()
    monkeypatch.setattr(onboarding, "async_session_factory", lambda: DummySessionCtx(session))

    ready = await onboarding.is_specialist_ready(specialist_id)

    assert ready is False


@pytest.mark.asyncio
async def test_is_specialist_ready_true_when_all_requirements_met(monkeypatch):
    specialist_id = uuid.uuid4()

    class Session:
        def __init__(self):
            self.calls = 0

        async def execute(self, _query):
            self.calls += 1
            values = [specialist_id, specialist_id, specialist_id]
            return DummyScalarResult(values[self.calls - 1])

    session = Session()
    monkeypatch.setattr(onboarding, "async_session_factory", lambda: DummySessionCtx(session))

    ready = await onboarding.is_specialist_ready(specialist_id)

    assert ready is True


@pytest.mark.asyncio
async def test_finalize_specialist_if_ready_switches_onboarding_to_active(monkeypatch):
    specialist_id = uuid.uuid4()

    captured = {}

    class Session:
        committed = False

        async def get(self, model, sid):
            assert sid == specialist_id
            name = getattr(model, "__name__", "")
            if name == "Specialist":
                return types.SimpleNamespace(status=SpecialistStatus.onboarding)
            if name == "SpecialistCalendarSettings":
                return types.SimpleNamespace(calendar_time_zone="Europe/Berlin")
            if name == "SpecialistProfile":
                return types.SimpleNamespace(public_name="Name", owner_tg_user_id=123)
            if name == "SpecialistAuthTelegram":
                return types.SimpleNamespace(tg_user_id=123)
            return None

        async def commit(self):
            self.committed = True

    async def _apply_defaults(session, sid, *, preferred_timezone=None):
        captured["sid"] = sid
        captured["preferred_timezone"] = preferred_timezone

    session = Session()
    monkeypatch.setattr(onboarding, "is_specialist_ready", lambda _sid: _ready_true())
    monkeypatch.setattr(onboarding, "async_session_factory", lambda: DummySessionCtx(session))
    monkeypatch.setattr(onboarding, "apply_specialist_defaults_if_missing", _apply_defaults)

    changed = await onboarding.finalize_specialist_if_ready(specialist_id)

    assert changed is True
    assert session.committed is True
    assert captured == {"sid": specialist_id, "preferred_timezone": "Europe/Berlin"}


@pytest.mark.asyncio
async def test_finalize_specialist_if_ready_is_idempotent_for_active(monkeypatch):
    specialist_id = uuid.uuid4()

    class Session:
        async def get(self, model, sid):
            assert sid == specialist_id
            return types.SimpleNamespace(status=SpecialistStatus.active)

        async def commit(self):
            raise AssertionError("commit should not be called")

    monkeypatch.setattr(onboarding, "is_specialist_ready", lambda _sid: _ready_true())
    monkeypatch.setattr(onboarding, "async_session_factory", lambda: DummySessionCtx(Session()))

    changed = await onboarding.finalize_specialist_if_ready(specialist_id)

    assert changed is False


async def _ready_true():
    return True


@pytest.mark.asyncio
async def test_finalize_specialist_if_ready_does_not_activate_without_smoke_ok(monkeypatch):
    specialist_id = uuid.uuid4()

    class Session:
        async def get(self, model, sid):
            raise AssertionError("session.get should not be called when specialist is not ready")

    monkeypatch.setattr(onboarding, "is_specialist_ready", lambda _sid: _ready_false())
    monkeypatch.setattr(onboarding, "async_session_factory", lambda: DummySessionCtx(Session()))

    changed = await onboarding.finalize_specialist_if_ready(specialist_id)

    assert changed is False


async def _ready_false():
    return False
