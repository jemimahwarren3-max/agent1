import pytest
from cryptography.fernet import Fernet

from app.core import crypto
from app.core.config import settings


def test_encrypt_decrypt_roundtrip(monkeypatch):
    monkeypatch.setattr(settings, "TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    raw = "super-secret-refresh-token"
    encrypted = crypto.encrypt_token(raw)
    assert encrypted != raw.encode()
    assert crypto.decrypt_token(encrypted) == raw


def test_missing_key_raises(monkeypatch):
    monkeypatch.setattr(settings, "TOKEN_ENCRYPTION_KEY", "")
    with pytest.raises(RuntimeError):
        crypto.encrypt_token("anything")
