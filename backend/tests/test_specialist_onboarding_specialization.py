import os
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("ENCRYPTION_KEY", "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=")
os.environ.setdefault("MASTER_BOT_TOKEN", "123456:test-master-token")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-google-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-google-client-secret")

import handlers.master_onboarding as onboarding


class DummyState:
    def __init__(self):
        self.current = None

    async def get_state(self):
        return self.current

    async def set_state(self, state):
        self.current = state.state if hasattr(state, "state") else state


class DummyMessage:
    def __init__(self, text: str, tg_user_id: int = 101):
        self.text = text
        self.from_user = types.SimpleNamespace(id=tg_user_id, username="spec", first_name="Spec", last_name="User")
        self.bot = types.SimpleNamespace(id=9001)
        self.answers = []

    async def answer(self, text, **kwargs):
        self.answers.append((text, kwargs))


class _Result:
    def __init__(self, one=None, one_or_none=None):
        self._one = one
        self._one_or_none = one_or_none

    def scalar_one(self):
        return self._one

    def scalar_one_or_none(self):
        return self._one_or_none


class _FakeSession:
    def __init__(self, auth_entry, specialist, profile=None):
        self.auth_entry = auth_entry
        self.specialist = specialist
        self.profile = profile
        self.commits = 0

    async def execute(self, stmt):
        sql = str(stmt)
        if "FROM specialist_auth_telegram" in sql and "JOIN" not in sql:
            return _Result(one=self.auth_entry)
        if "FROM specialist_profile" in sql:
            return _Result(one_or_none=self.profile)
        if "JOIN specialist_auth_telegram" in sql:
            return _Result(one=self.specialist)
        raise AssertionError(f"Unexpected SQL: {sql}")

    def add(self, obj):
        self.profile = obj

    async def commit(self):
        self.commits += 1

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_onboarding_name_then_specialization_transitions_and_saves(monkeypatch):
    state = DummyState()
    await state.set_state(onboarding.OnboardingStates.waiting_for_public_name)

    specialist_id = "sp-1"
    auth_entry = types.SimpleNamespace(specialist_id=specialist_id)
    specialist = types.SimpleNamespace(specialist_id=specialist_id, specialization=None)
    session = _FakeSession(auth_entry=auth_entry, specialist=specialist, profile=None)

    monkeypatch.setattr(onboarding, "async_session_factory", lambda: session)
    
    async def _fake_log(*args, **kwargs):
        return None
    monkeypatch.setattr(onboarding, "log_outbound_message", _fake_log)

    msg_name = DummyMessage(text="Анна")
    await onboarding.process_public_name(msg_name, state)

    assert await state.get_state() == onboarding.OnboardingStates.waiting_for_specialization.state
    assert session.profile is not None
    assert session.profile.public_name == "Анна"

    msg_spec = DummyMessage(text="Психолог")
    await onboarding.process_specialization(msg_spec, state)

    assert await state.get_state() == onboarding.OnboardingStates.waiting_for_bot_token.state
    assert specialist.specialization == "Психолог"


@pytest.mark.asyncio
async def test_onboarding_specialization_validation_too_long_keeps_state(monkeypatch):
    state = DummyState()
    await state.set_state(onboarding.OnboardingStates.waiting_for_specialization)

    
    async def _fake_log(*args, **kwargs):
        return None
    monkeypatch.setattr(onboarding, "log_outbound_message", _fake_log)

    msg = DummyMessage(text="a" * 121)
    await onboarding.process_specialization(msg, state)

    assert await state.get_state() == onboarding.OnboardingStates.waiting_for_specialization.state


@pytest.mark.asyncio
async def test_onboarding_specialization_validation_bad_chars_keeps_state(monkeypatch):
    state = DummyState()
    await state.set_state(onboarding.OnboardingStates.waiting_for_specialization)

    
    async def _fake_log(*args, **kwargs):
        return None
    monkeypatch.setattr(onboarding, "log_outbound_message", _fake_log)

    msg = DummyMessage(text="<script>alert(1)</script>")
    await onboarding.process_specialization(msg, state)

    assert await state.get_state() == onboarding.OnboardingStates.waiting_for_specialization.state
