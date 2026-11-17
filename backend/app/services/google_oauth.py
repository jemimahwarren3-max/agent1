"""Google OAuth 2.0 flow for Gmail/Sheets/Drive access. Access/refresh tokens
are never returned to the frontend — callers persist them encrypted via
app.core.crypto and read them back the same way."""

from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from app.core.config import settings

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]


class GoogleOAuthNotConfiguredError(RuntimeError):
    pass


def _require_configured() -> None:
    if not settings.GOOGLE_OAUTH_CLIENT_ID or not settings.GOOGLE_OAUTH_CLIENT_SECRET:
        raise GoogleOAuthNotConfiguredError(
            "GOOGLE_OAUTH_CLIENT_ID / GOOGLE_OAUTH_CLIENT_SECRET are not set — see "
            "docs/GOOGLE_CLOUD_SETUP.md."
        )


def _client_config() -> dict:
    return {
        "web": {
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.GOOGLE_OAUTH_REDIRECT_URI],
        }
    }


def _build_flow() -> Flow:
    return Flow.from_client_config(
        _client_config(), scopes=GOOGLE_SCOPES, redirect_uri=settings.GOOGLE_OAUTH_REDIRECT_URI
    )


def build_authorize_url(state: str) -> str:
    _require_configured()
    flow = _build_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline", include_granted_scopes="true", prompt="consent", state=state
    )
    return auth_url


def exchange_code_for_credentials(code: str) -> Credentials:
    _require_configured()
    flow = _build_flow()
    flow.fetch_token(code=code)
    return flow.credentials


def refresh_credentials(credentials: Credentials) -> Credentials:
    """Refreshes in place if expired and a refresh token is available."""
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(GoogleAuthRequest())
    return credentials


def credentials_from_tokens(
    access_token: str, refresh_token: str | None, scopes: list[str]
) -> Credentials:
    _require_configured()
    return Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
        client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET,
        scopes=scopes,
    )
