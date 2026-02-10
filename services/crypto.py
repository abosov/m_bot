import os

from cryptography.fernet import Fernet

import config

_cipher = None
_cipher_key = None


def _resolve_key() -> str:
    key = config.ENCRYPTION_KEY or os.getenv("ENCRYPTION_KEY")
    if key:
        return key

    raise RuntimeError(
        "ENCRYPTION_KEY is required to encrypt/decrypt tokens. "
        "Set ENCRYPTION_KEY in environment."
    )


def _get_cipher() -> Fernet:
    global _cipher, _cipher_key
    key = _resolve_key()

    if _cipher is not None and _cipher_key == key:
        return _cipher

    _cipher = Fernet(key)
    _cipher_key = key
    return _cipher


def encrypt_token(token: str) -> str:
    """Шифрует токен бота для сохранения в БД."""
    return _get_cipher().encrypt(token.encode("utf-8")).decode("utf-8")


def decrypt_token(encrypted_token: str) -> str:
    """Расшифровывает токен бота."""
    return _get_cipher().decrypt(encrypted_token.encode("utf-8")).decode("utf-8")
