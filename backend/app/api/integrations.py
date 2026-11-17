"""Google OAuth connect/disconnect for Gmail/Sheets/Drive. The authorize step
is behind a normal JWT-authenticated endpoint; the callback is not (Google
redirects the browser straight to it with no Authorization header), so the
organisation is recovered from a signed `state` token instead — see
app.core.security.create_oauth_state_token."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto import encrypt_token
from app.core.deps import get_current_user
from app.core.security import create_oauth_state_token, decode_oauth_state_token
from app.db.session import get_db
from app.models.core import User
from app.models.integrations import Integration, IntegrationProvider, IntegrationStatus, OAuthToken
from app.schemas.integration import AuthorizeUrlResponse, IntegrationResponse
from app.services import gmail_service
from app.services.google_oauth import (
    GOOGLE_SCOPES,
    GoogleOAuthNotConfiguredError,
    build_authorize_url,
    exchange_code_for_credentials,
)

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


@router.get("", response_model=list[IntegrationResponse])
def list_integrations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(Integration).filter(Integration.organisation_id == current_user.organisation_id).all()
    )


@router.get("/google/authorize", response_model=AuthorizeUrlResponse)
def google_authorize(current_user: User = Depends(get_current_user)):
    state = create_oauth_state_token(str(current_user.organisation_id))
    try:
        return AuthorizeUrlResponse(authorize_url=build_authorize_url(state))
    except GoogleOAuthNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/google/callback")
def google_callback(code: str, state: str, db: Session = Depends(get_db)):
    try:
        organisation_id = uuid.UUID(decode_oauth_state_token(state))
    except (JWTError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    try:
        credentials = exchange_code_for_credentials(code)
    except GoogleOAuthNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    account_email = gmail_service.get_profile_email(credentials)

    integration = (
        db.query(Integration)
        .filter(
            Integration.organisation_id == organisation_id,
            Integration.provider == IntegrationProvider.GOOGLE_WORKSPACE,
        )
        .first()
    )
    if integration is None:
        integration = Integration(
            organisation_id=organisation_id, provider=IntegrationProvider.GOOGLE_WORKSPACE
        )
        db.add(integration)

    integration.status = IntegrationStatus.CONNECTED
    integration.connected_account_email = account_email
    integration.scopes = credentials.scopes or GOOGLE_SCOPES
    db.flush()

    token = db.query(OAuthToken).filter(OAuthToken.integration_id == integration.id).first()
    if token is None:
        token = OAuthToken(integration_id=integration.id)
        db.add(token)

    token.encrypted_access_token = encrypt_token(credentials.token)
    if credentials.refresh_token:
        token.encrypted_refresh_token = encrypt_token(credentials.refresh_token)
    token.token_expiry = credentials.expiry.isoformat() if credentials.expiry else None
    token.is_revoked = False
    db.commit()

    frontend_url = settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else "http://localhost:3000"
    return RedirectResponse(url=f"{frontend_url}/integrations?connected=1")


@router.post("/{integration_id}/disconnect", response_model=IntegrationResponse)
def disconnect_integration(
    integration_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    integration = (
        db.query(Integration)
        .filter(Integration.id == integration_id, Integration.organisation_id == current_user.organisation_id)
        .first()
    )
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    integration.status = IntegrationStatus.DISCONNECTED
    token = db.query(OAuthToken).filter(OAuthToken.integration_id == integration.id).first()
    if token:
        token.is_revoked = True
    db.commit()
    db.refresh(integration)
    return integration
