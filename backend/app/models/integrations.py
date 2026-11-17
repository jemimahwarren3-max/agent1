import uuid
import enum

from sqlalchemy import String, ForeignKey, JSON, LargeBinary, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.mixins import UUIDPKMixin, TimestampMixin, str_enum


class IntegrationProvider(str, enum.Enum):
    GOOGLE_WORKSPACE = "google_workspace"


class IntegrationStatus(str, enum.Enum):
    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    ERROR = "error"


class Integration(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "integrations"

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id"), nullable=False, index=True
    )
    provider: Mapped[IntegrationProvider] = mapped_column(
        str_enum(IntegrationProvider, "integration_provider"), nullable=False
    )
    status: Mapped[IntegrationStatus] = mapped_column(
        str_enum(IntegrationStatus, "integration_status"),
        default=IntegrationStatus.DISCONNECTED,
        nullable=False,
    )
    connected_account_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    scopes: Mapped[list] = mapped_column(JSON, default=list)
    config: Mapped[dict] = mapped_column(JSON, default=dict)


class OAuthToken(UUIDPKMixin, TimestampMixin, Base):
    """Refresh/access tokens, always stored encrypted. Never serialize these to API responses."""

    __tablename__ = "oauth_tokens"

    integration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("integrations.id"), nullable=False, unique=True
    )
    encrypted_access_token: Mapped[bytes] = mapped_column(LargeBinary, nullable=True)
    encrypted_refresh_token: Mapped[bytes] = mapped_column(LargeBinary, nullable=True)
    token_expiry: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
