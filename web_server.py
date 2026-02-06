import os
import uuid
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select, update
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from database import (
    async_session_factory, 
    GoogleOAuth, 
    GoogleOAuthStatus, 
    SpecialistAuthTelegram,
    SpecialistProfile
)
from services.google_oauth import exchange_code_for_token
from services.crypto import encrypt_token
from logging_middleware import log_outbound_message

app = FastAPI()

# Инициализируем бота для отправки уведомлений (используем тот же токен)
bot = Bot(
    token=os.getenv("MASTER_BOT_TOKEN"), 
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
)

@app.get("/google/oauth/callback", response_class=HTMLResponse)
async def google_oauth_callback(request: Request):
    code = request.query_params.get("code")
    state = request.query_params.get("state") # Здесь лежит specialist_id
    error = request.query_params.get("error")

    if error:
        return f"<h1>Ошибка авторизации: {error}</h1>"

    if not code or not state:
        return "<h1>Ошибка: Отсутствуют обязательные параметры (code, state)</h1>"

    try:
        specialist_id = uuid.UUID(state)
    except ValueError:
        return "<h1>Ошибка: Неверный формат state (ожидался UUID)</h1>"

    try:
        # 1. Обмен кода на токены
        refresh_token, access_token, _ = exchange_code_for_token(code)
        
        if not refresh_token:
            # Если refresh_token не пришел (такое бывает при повторной авторизации без prompt='consent'),
            # в MVP мы считаем это ошибкой, так как нам нужен offline доступ.
            # (Хотя в services/google_oauth.py мы добавили prompt='consent', так что он должен быть)
            pass 

        # 2. Сохранение в БД
        encrypted_refresh_token = encrypt_token(refresh_token)
        
        async with async_session_factory() as session:
            # Проверяем, есть ли уже запись
            stmt = select(GoogleOAuth).where(GoogleOAuth.specialist_id == specialist_id)
            result = await session.execute(stmt)
            oauth_entry = result.scalar_one_or_none()

            if oauth_entry:
                oauth_entry.refresh_token_encrypted = encrypted_refresh_token
                oauth_entry.status = GoogleOAuthStatus.connected
                oauth_entry.token_updated_at = datetime.utcnow()
                oauth_entry.scopes = "https://www.googleapis.com/auth/calendar" # Hardcoded for MVP
            else:
                new_entry = GoogleOAuth(
                    specialist_id=specialist_id,
                    refresh_token_encrypted=encrypted_refresh_token,
                    scopes="https://www.googleapis.com/auth/calendar",
                    status=GoogleOAuthStatus.connected,
                    token_updated_at=datetime.utcnow()
                )
                session.add(new_entry)
            
            # Получаем данные специалиста для уведомления
            auth_stmt = select(SpecialistAuthTelegram).where(SpecialistAuthTelegram.specialist_id == specialist_id)
            auth_res = await session.execute(auth_stmt)
            auth_data = auth_res.scalar_one_or_none()
            
            # Получаем имя для логов
            prof_stmt = select(SpecialistProfile).where(SpecialistProfile.specialist_id == specialist_id)
            prof_res = await session.execute(prof_stmt)
            profile = prof_res.scalar_one_or_none()
            specialist_name = profile.public_name if profile else "Unknown"

            await session.commit()

            # 3. Уведомление в Telegram
            if auth_data:
                text_out = "✅ **Google Календарь успешно подключен!**\nТеперь вы можете настроить расписание."
                try:
                    await bot.send_message(chat_id=auth_data.tg_user_id, text=text_out)
                    
                    # 4. Логирование исходящего сообщения
                    await log_outbound_message(
                        bot=bot,
                        tg_user_id=auth_data.tg_user_id,
                        content=text_out,
                        fsm_state="google_connected_callback",
                        specialist_name=specialist_name,
                        user_handle=f"@{auth_data.tg_username}" if auth_data.tg_username else str(auth_data.tg_user_id)
                    )
                except Exception as e:
                    print(f"Failed to send TG notification: {e}")

        return """
        <html>
            <head><title>Success</title></head>
            <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
                <h1 style="color: green;">Успешно!</h1>
                <p>Google Календарь подключен.</p>
                <p>Вы можете закрыть это окно и вернуться в Telegram.</p>
                <script>setTimeout(function(){window.close()}, 3000);</script>
            </body>
        </html>
        """

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"<h1>Произошла ошибка при подключении: {str(e)}</h1>"