from typing import Tuple, Any
from google_auth_oauthlib.flow import Flow

import config

# Конфигурация клиента Google из переменных окружения
# В продакшене лучше использовать файл client_secrets.json, но для MVP соберем словарь вручную
GOOGLE_CLIENT_CONFIG = {
    "web": {
        "client_id": config.GOOGLE_CLIENT_ID,
        "client_secret": config.GOOGLE_CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [config.GOOGLE_REDIRECT_URI],
    }
}

SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
]
REDIRECT_URI = config.GOOGLE_REDIRECT_URI


def _ensure_google_oauth_config() -> None:
    if not config.GOOGLE_CLIENT_ID or not config.GOOGLE_CLIENT_SECRET:
        if config.APP_ENV == "prod":
            raise RuntimeError(
                "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are required in production."
            )

def get_auth_url(specialist_id: str) -> str:
    """
    Генерирует ссылку для авторизации в Google.
    В state зашиваем specialist_id.
    """
    _ensure_google_oauth_config()
    flow = Flow.from_client_config(
        GOOGLE_CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    
    # access_type='offline' обязателен для получения refresh_token
    # prompt='consent' заставляет Google всегда спрашивать разрешение (чтобы гарантированно дали refresh_token)
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent',
        state=str(specialist_id)
    )
    
    return authorization_url

def exchange_code_for_token(code: str) -> Tuple[str, str, Any]:
    """
    Обменивает временный код на токены.
    Возвращает (refresh_token, access_token, credentials_object)
    """
    _ensure_google_oauth_config()
    flow = Flow.from_client_config(
        GOOGLE_CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    
    flow.fetch_token(code=code)
    creds = flow.credentials
    
    return creds.refresh_token, creds.token, creds
