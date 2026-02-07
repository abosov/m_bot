import os
import json
from typing import Tuple, Dict, Any
from google_auth_oauthlib.flow import Flow
from dotenv import load_dotenv

from config import GOOGLE_REDIRECT_URI

load_dotenv()
load_dotenv(".env.local")

# Конфигурация клиента Google из переменных окружения
# В продакшене лучше использовать файл client_secrets.json, но для MVP соберем словарь вручную
GOOGLE_CLIENT_CONFIG = {
    "web": {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [GOOGLE_REDIRECT_URI],
    }
}

SCOPES = ['https://www.googleapis.com/auth/calendar']
REDIRECT_URI = GOOGLE_REDIRECT_URI

def get_auth_url(specialist_id: str) -> str:
    """
    Генерирует ссылку для авторизации в Google.
    В state зашиваем specialist_id.
    """
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
    flow = Flow.from_client_config(
        GOOGLE_CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    
    flow.fetch_token(code=code)
    creds = flow.credentials
    
    return creds.refresh_token, creds.token, creds
