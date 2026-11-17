from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, organisation_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": subject, "org": organisation_id, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])


def create_oauth_state_token(organisation_id: str) -> str:
    """Short-lived, signed `state` param for the Google OAuth redirect — the
    callback request comes straight from Google with no Authorization header,
    so this is how we recover which organisation initiated the flow."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=10)
    payload = {"org": organisation_id, "purpose": "google_oauth_state", "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_oauth_state_token(token: str) -> str:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    if payload.get("purpose") != "google_oauth_state":
        raise jwt.JWTError("Not an OAuth state token")
    return payload["org"]
