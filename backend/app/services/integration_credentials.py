"""Loads a usable, refreshed google.oauth2.credentials.Credentials for an
Integration — the one place that decrypts stored tokens and re-encrypts
whatever Google hands back after a refresh."""

from google.oauth2.credentials import Credentials
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_token, encrypt_token
from app.models.integrations import Integration, IntegrationStatus, OAuthToken
from app.services.google_oauth import credentials_from_tokens, refresh_credentials


class IntegrationNotConnectedError(RuntimeError):
    pass


def get_valid_credentials(db: Session, integration: Integration) -> Credentials:
    if integration.status != IntegrationStatus.CONNECTED:
        raise IntegrationNotConnectedError(f"Integration {integration.id} is not connected.")

    token = db.query(OAuthToken).filter(OAuthToken.integration_id == integration.id).first()
    if token is None or token.is_revoked:
        raise IntegrationNotConnectedError(f"Integration {integration.id} has no valid token.")

    credentials = credentials_from_tokens(
        access_token=decrypt_token(token.encrypted_access_token),
        refresh_token=decrypt_token(token.encrypted_refresh_token) if token.encrypted_refresh_token else None,
        scopes=integration.scopes,
    )

    credentials = refresh_credentials(credentials)
    if credentials.token:
        token.encrypted_access_token = encrypt_token(credentials.token)
        if credentials.expiry:
            token.token_expiry = credentials.expiry.isoformat()
        db.commit()

    return credentials
