import types
import uuid

import pytest
from aiogram.types import Message

import logging_middleware


class DummySession:
    def __init__(self, store):
        self.store = store

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, stmt):
        return types.SimpleNamespace(first=lambda: None)

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        self.store["log"] = obj

    async def flush(self):
        return None

    async def commit(self):
        return None

    async def get(self, model, key):
        return self.store.get("log")


@pytest.mark.asyncio
async def test_struct_logging_middleware_error_path_sets_flags_and_reraises(monkeypatch):
    store = {}

    monkeypatch.setattr(logging_middleware, "async_session_factory", lambda: DummySession(store))

    async def _get_specialist_info_stub(bot_id):
        return None

    monkeypatch.setattr(logging_middleware, "_get_specialist_info", _get_specialist_info_stub)

    notify_calls = []

    async def _notify_exception_stub(**kwargs):
        notify_calls.append(kwargs)

    monkeypatch.setattr(logging_middleware, "notify_exception", _notify_exception_stub)

    middleware = logging_middleware.StructLoggingMiddleware()

    event = Message.model_validate(
        {
            "message_id": 1,
            "date": 0,
            "chat": {"id": 101, "type": "private"},
            "from": {"id": 202, "is_bot": False, "first_name": "Test"},
            "text": "boom",
        }
    )

    class BotStub:
        id = 999

        async def get_me(self):
            return types.SimpleNamespace(username="test_bot")

    boom = RuntimeError("handler failed")

    async def failing_handler(evt, data):
        raise boom

    with pytest.raises(RuntimeError) as exc_info:
        await middleware(failing_handler, event, {"bot": BotStub()})

    assert exc_info.value is boom
    assert len(notify_calls) == 1

    log_entry = store["log"]
    assert log_entry.is_error is True
    assert log_entry.error_details
    assert isinstance(log_entry.processing_time, float)
