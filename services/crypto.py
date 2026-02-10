import os

from cryptography.fernet import Fernet

import config

_TEST_FERNET_KEY = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
_cipher = None
_cipher_key = None


def _resolve_key() -> str:
    key = config.ENCRYPTION_KEY or os.getenv("ENCRYPTION_KEY")
    if key:
        return key

    if config.is_test_env():
        return _TEST_FERNET_KEY

    raise RuntimeError("ENCRYPTION_KEY is required for encryption. Set ENCRYPTION_KEY in env.")


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
