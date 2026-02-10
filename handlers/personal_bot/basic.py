from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import (
    GoogleOAuthStatus,
    Specialist,
    TelegramBot,
    TelegramBotStatus,
    async_session_factory,
)

router = Router(name="personal_bot_basic")

_SUPPORT_URL = "https://t.me/zumbot_support"


def _status_to_text(value) -> str:
    if value is None:
        return "—"
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


async def _load_specialist_state(specialist_id):
    async with async_session_factory() as session:
        specialist_stmt = (
            select(Specialist)
            .options(
                selectinload(Specialist.google_oauth),
                selectinload(Specialist.calendar_settings),
            )
            .where(Specialist.specialist_id == specialist_id)
        )
        specialist = (await session.execute(specialist_stmt)).scalar_one_or_none()

        bot_stmt = (
            select(TelegramBot)
            .where(
                TelegramBot.specialist_id == specialist_id,
                TelegramBot.status == TelegramBotStatus.active,
            )
            .order_by(TelegramBot.updated_at.desc(), TelegramBot.created_at.desc())
        )
        active_bot = (await session.execute(bot_stmt)).scalars().first()

    return specialist, active_bot


@router.message(Command("start"))
async def personal_start(
    message: Message,
    actor: str,
    public_name: str | None,
) -> None:
    if actor == "specialist":
        display_name = public_name or "специалист"
        text = (
            f"👋 Панель специалиста, {display_name}.\n\n"
            "Доступно сейчас:\n"
            "• /status — состояние интеграций\n"
            "• /help — список команд\n\n"
            f"Поддержка: {_SUPPORT_URL}"
        )
        await message.answer(text)
        return

    await message.answer("👋 Запись скоро будет доступна. Пока это клиентская заглушка MVP.")


@router.message(Command("help"))
async def personal_help(message: Message, actor: str) -> None:
    if actor != "specialist":
        await message.answer("ℹ️ Скоро здесь появится клиентский сценарий записи.")
        return

    await message.answer(
        "Команды специалиста:\n"
        "• /start — панель специалиста\n"
        "• /status — статус профиля и интеграций\n"
        "• /help — эта справка\n\n"
        "В разработке: управление расписанием, клиентские записи и напоминания."
    )


@router.message(Command("status"))
@router.message(F.text == "Мой статус")
async def personal_status(message: Message, actor: str, specialist_id) -> None:
    if actor != "specialist":
        await message.answer("ℹ️ Команда доступна только специалисту-владельцу этого бота.")
        return

    specialist, active_bot = await _load_specialist_state(specialist_id)
    if specialist is None:
        await message.answer("⚠️ Профиль специалиста не найден.")
        return

    oauth_connected = (
        specialist.google_oauth is not None
        and specialist.google_oauth.status == GoogleOAuthStatus.connected
    )

    calendar_id = specialist.calendar_settings.calendar_id if specialist.calendar_settings else None
    calendar_summary = specialist.calendar_settings.calendar_summary if specialist.calendar_settings else None
    smoke_status = specialist.calendar_settings.last_smoke_test_status if specialist.calendar_settings else None

    bot_username = f"@{active_bot.bot_username}" if active_bot else "—"

    await message.answer(
        "📊 Состояние специалиста:\n"
        f"• Статус специалиста: {_status_to_text(specialist.status)}\n"
        f"• Personal bot: {bot_username}\n"
        f"• Google OAuth: {'connected' if oauth_connected else 'not_connected'}\n"
        f"• Календарь ID: {calendar_id or '—'}\n"
        f"• Календарь summary: {calendar_summary or '—'}\n"
        f"• Last smoke-test: {smoke_status or '—'}"
    )
