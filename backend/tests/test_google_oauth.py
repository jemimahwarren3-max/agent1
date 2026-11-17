from unittest.mock import MagicMock

import pytest

from app.core.config import settings
from app.services import google_oauth


@pytest.fixture(autouse=True)
def configured_oauth(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "fake-client-id")
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "fake-client-secret")


def test_build_authorize_url_raises_when_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")
    with pytest.raises(google_oauth.GoogleOAuthNotConfiguredError):
        google_oauth.build_authorize_url("some-state")


def test_build_authorize_url_includes_state(monkeypatch):
    fake_flow = MagicMock()
    fake_flow.authorization_url.return_value = ("https://accounts.google.com/o/oauth2/auth?...", None)
    monkeypatch.setattr(google_oauth, "_build_flow", lambda: fake_flow)

    url = google_oauth.build_authorize_url("my-state")

    assert url == "https://accounts.google.com/o/oauth2/auth?..."
    _, kwargs = fake_flow.authorization_url.call_args
    assert kwargs["state"] == "my-state"
    assert kwargs["access_type"] == "offline"


def test_exchange_code_for_credentials_returns_flow_credentials(monkeypatch):
    fake_flow = MagicMock()
    fake_flow.credentials = "the-credentials-object"
    monkeypatch.setattr(google_oauth, "_build_flow", lambda: fake_flow)

    result = google_oauth.exchange_code_for_credentials("auth-code")

    fake_flow.fetch_token.assert_called_once_with(code="auth-code")
    assert result == "the-credentials-object"


def test_refresh_credentials_only_refreshes_when_expired():
    not_expired = MagicMock(expired=False)
    google_oauth.refresh_credentials(not_expired)
    not_expired.refresh.assert_not_called()

    expired_with_refresh_token = MagicMock(expired=True, refresh_token="rt")
    google_oauth.refresh_credentials(expired_with_refresh_token)
    expired_with_refresh_token.refresh.assert_called_once()
