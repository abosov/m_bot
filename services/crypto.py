import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

# Получаем ключ из переменных окружения.
# Для генерации ключа можно использовать: Fernet.generate_key().decode()
_key = os.getenv("ENCRYPTION_KEY")

if not _key:
    raise ValueError("ENCRYPTION_KEY is not set in environment variables!")

_cipher = Fernet(_key)

def encrypt_token(token: str) -> str:
    """Шифрует токен бота для сохранения в БД."""
    return _cipher.encrypt(token.encode("utf-8")).decode("utf-8")

def decrypt_token(encrypted_token: str) -> str:
    """Расшифровывает токен бота."""
    return _cipher.decrypt(encrypted_token.encode("utf-8")).decode("utf-8")