from unittest.mock import MagicMock

import pytest
from cryptography.fernet import Fernet

from app.core.config import settings
from app.core.crypto import decrypt_token, encrypt_token
from app.models.core import Organisation
from app.models.integrations import Integration, IntegrationProvider, IntegrationStatus, OAuthToken
from app.services import integration_credentials


@pytest.fixture(autouse=True)
def encryption_key(monkeypatch):
    monkeypatch.setattr(settings, "TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "fake-client-id")
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "fake-client-secret")


@pytest.fixture()
def connected_integration(db_session):
    org = Organisation(name="Haki Systems")
    db_session.add(org)
    db_session.flush()

    integration = Integration(
        organisation_id=org.id,
        provider=IntegrationProvider.GOOGLE_WORKSPACE,
        status=IntegrationStatus.CONNECTED,
        connected_account_email="sales@hakisystems.co.zw",
        scopes=["https://www.googleapis.com/auth/gmail.send"],
    )
    db_session.add(integration)
    db_session.flush()

    token = OAuthToken(
        integration_id=integration.id,
        encrypted_access_token=encrypt_token("old-access-token"),
        encrypted_refresh_token=encrypt_token("a-refresh-token"),
    )
    db_session.add(token)
    db_session.commit()
    return integration, token


def test_disconnected_integration_raises(db_session):
    org = Organisation(name="Haki Systems")
    db_session.add(org)
    db_session.flush()
    integration = Integration(
        organisation_id=org.id, provider=IntegrationProvider.GOOGLE_WORKSPACE, status=IntegrationStatus.DISCONNECTED
    )
    db_session.add(integration)
    db_session.commit()

    with pytest.raises(integration_credentials.IntegrationNotConnectedError):
        integration_credentials.get_valid_credentials(db_session, integration)


def test_revoked_token_raises(db_session, connected_integration):
    integration, token = connected_integration
    token.is_revoked = True
    db_session.commit()

    with pytest.raises(integration_credentials.IntegrationNotConnectedError):
        integration_credentials.get_valid_credentials(db_session, integration)


def test_refreshed_token_is_re_encrypted_and_persisted(db_session, connected_integration, monkeypatch):
    integration, token = connected_integration

    def fake_refresh(credentials):
        credentials.token = "new-access-token"
        return credentials

    monkeypatch.setattr(integration_credentials, "refresh_credentials", fake_refresh)

    credentials = integration_credentials.get_valid_credentials(db_session, integration)

    assert credentials.token == "new-access-token"
    db_session.refresh(token)
    assert decrypt_token(token.encrypted_access_token) == "new-access-token"
