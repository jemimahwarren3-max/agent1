"""Symmetric encryption for OAuth tokens at rest. Never store Google refresh
tokens in plaintext — the brief is explicit about this."""

from cryptography.fernet import Fernet

from app.core.config import settings


def _get_fernet() -> Fernet:
    if not settings.TOKEN_ENCRYPTION_KEY:
        raise RuntimeError(
            "TOKEN_ENCRYPTION_KEY is not set. Generate one with "
            "`python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"` "
            "and put it in your .env file."
        )
    return Fernet(settings.TOKEN_ENCRYPTION_KEY.encode())


def encrypt_token(raw_token: str) -> bytes:
    return _get_fernet().encrypt(raw_token.encode())


def decrypt_token(encrypted_token: bytes) -> str:
    return _get_fernet().decrypt(encrypted_token).decode()
