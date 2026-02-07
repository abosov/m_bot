import os

from dotenv import load_dotenv

load_dotenv()
load_dotenv(".env.local")

BACKEND_BASE_URL = os.getenv("BASE_URL", "https://api.zumbot.ru")
PUBLIC_SITE_URL = os.getenv("PUBLIC_SITE_URL", "https://zumbot.ru")
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI",
    "https://api.zumbot.ru/google/oauth/callback",
)
