import pytest
from jose import JWTError

from app.core.security import (
    create_access_token,
    create_oauth_state_token,
    decode_access_token,
    decode_oauth_state_token,
    hash_password,
    verify_password,
)


def test_hash_password_and_verify_roundtrip():
    hashed = hash_password("correct-password")
    assert hashed != "correct-password"
    assert verify_password("correct-password", hashed)
    assert not verify_password("wrong-password", hashed)


def test_access_token_roundtrip():
    token = create_access_token(subject="user-123", organisation_id="org-456")
    payload = decode_access_token(token)
    assert payload["sub"] == "user-123"
    assert payload["org"] == "org-456"


def test_tampered_token_rejected():
    token = create_access_token(subject="user-123", organisation_id="org-456")
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    with pytest.raises(JWTError):
        decode_access_token(tampered)


def test_oauth_state_token_roundtrip():
    state = create_oauth_state_token("org-789")
    assert decode_oauth_state_token(state) == "org-789"


def test_oauth_state_token_rejects_a_regular_access_token():
    # An access token has no "purpose" claim, so it must not be accepted as state.
    token = create_access_token(subject="user-123", organisation_id="org-456")
    with pytest.raises(JWTError):
        decode_oauth_state_token(token)
