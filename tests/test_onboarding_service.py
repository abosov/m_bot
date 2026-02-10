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


@pytest.mark.asyncio
async def test_finalize_specialist_if_ready_switches_onboarding_to_active(monkeypatch):
    specialist_id = uuid.uuid4()

    class Session:
        committed = False

        async def get(self, model, sid):
            assert sid == specialist_id
            return types.SimpleNamespace(status=SpecialistStatus.onboarding)

        async def commit(self):
            self.committed = True

    session = Session()
    monkeypatch.setattr(onboarding, "is_specialist_ready", lambda _sid: _ready_true())
    monkeypatch.setattr(onboarding, "async_session_factory", lambda: DummySessionCtx(session))

    changed = await onboarding.finalize_specialist_if_ready(specialist_id)

    assert changed is True
    assert session.committed is True


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
