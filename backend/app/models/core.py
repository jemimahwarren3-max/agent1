import uuid
import enum

from sqlalchemy import String, ForeignKey, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import UUIDPKMixin, TimestampMixin, str_enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    MEMBER = "member"


class Organisation(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "organisations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="organisation")
    company_profile: Mapped["CompanyProfile"] = relationship(
        back_populates="organisation", uselist=False
    )


class User(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "users"

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        str_enum(UserRole, "user_role"), default=UserRole.MEMBER, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    organisation: Mapped["Organisation"] = relationship(back_populates="users")


class CompanyProfile(UUIDPKMixin, TimestampMixin, Base):
    """Editable company context used by every agent — services, markets, messaging.

    Kept separate from source code so the administrator can update positioning
    without a deploy, per the brief's requirement.
    """

    __tablename__ = "company_profiles"

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id"), unique=True, nullable=False
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    website: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    phone_numbers: Mapped[list] = mapped_column(JSON, default=list)
    services: Mapped[list] = mapped_column(JSON, default=list)
    target_industries: Mapped[list] = mapped_column(JSON, default=list)
    target_markets: Mapped[list] = mapped_column(JSON, default=list)
    outreach_messaging_notes: Mapped[str] = mapped_column(String(2000), nullable=False, default="")

    organisation: Mapped["Organisation"] = relationship(back_populates="company_profile")


class AuditLog(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "audit_logs"

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id"), nullable=False, index=True
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
