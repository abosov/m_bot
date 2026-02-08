from cryptography.fernet import Fernet
import config

# Получаем ключ из переменных окружения.
# Для генерации ключа можно использовать: Fernet.generate_key().decode()
_key = config.ENCRYPTION_KEY

if not _key:
    message = "ENCRYPTION_KEY is required for encryption. Set ENCRYPTION_KEY in env."
    if config.APP_ENV == "prod":
        raise RuntimeError(message)
    raise ValueError(message)

_cipher = Fernet(_key)

def encrypt_token(token: str) -> str:
    """Шифрует токен бота для сохранения в БД."""
    return _cipher.encrypt(token.encode("utf-8")).decode("utf-8")

def decrypt_token(encrypted_token: str) -> str:
    """Расшифровывает токен бота."""
    return _cipher.decrypt(encrypted_token.encode("utf-8")).decode("utf-8")
