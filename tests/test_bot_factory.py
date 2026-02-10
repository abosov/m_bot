import pytest

from services.telegram import bot_factory


class DummyTelegramBot:
    def __init__(self, bot_user_id: int):
        self.bot_user_id = bot_user_id
        self.bot_token_encrypted = "encrypted"


class DummySession:
    def __init__(self):
        self.closed = False

    async def close(self):
        self.closed = True


class DummyBot:
    def __init__(self):
        self.session = DummySession()


@pytest.mark.asyncio
async def test_get_personal_bot_returns_cached_instance(monkeypatch):
    bot_factory._personal_bot_cache.clear()
    now = 100.0
    monkeypatch.setattr(bot_factory.time, "monotonic", lambda: now)
    monkeypatch.setattr(bot_factory, "build_personal_bot", lambda tg_bot: DummyBot())

    tg_bot = DummyTelegramBot(bot_user_id=42)

    bot1 = await bot_factory.get_personal_bot(tg_bot)
    bot2 = await bot_factory.get_personal_bot(tg_bot)

    assert bot1 is bot2
    expires_at, _ = bot_factory._personal_bot_cache[tg_bot.bot_user_id]
    assert expires_at == pytest.approx(now + bot_factory._PERSONAL_BOT_CACHE_TTL_SEC)

    await bot_factory.close_personal_bot_cache()


@pytest.mark.asyncio
async def test_get_personal_bot_expires_and_closes_session(monkeypatch):
    bot_factory._personal_bot_cache.clear()
    current_time = {"value": 100.0}
    monkeypatch.setattr(bot_factory.time, "monotonic", lambda: current_time["value"])

    created_bots: list[DummyBot] = []

    def _build(_):
        bot = DummyBot()
        created_bots.append(bot)
        return bot

    monkeypatch.setattr(bot_factory, "build_personal_bot", _build)

    tg_bot = DummyTelegramBot(bot_user_id=77)

    first_bot = await bot_factory.get_personal_bot(tg_bot)
    current_time["value"] += bot_factory._PERSONAL_BOT_CACHE_TTL_SEC + 1
    second_bot = await bot_factory.get_personal_bot(tg_bot)

    assert first_bot is not second_bot
    assert created_bots[0].session.closed is True

    await bot_factory.close_personal_bot_cache()
