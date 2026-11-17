import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


def str_enum(enum_cls, name: str) -> Enum:
    """Enum column that stores each member's string `.value` ("admin") in Postgres,
    instead of SQLAlchemy's default of the member `.name` ("ADMIN") — the enums here
    are `class X(str, enum.Enum)` and every API/query comparison uses the lowercase
    value, so the column must match or filters silently never match."""
    return Enum(enum_cls, name=name, values_callable=lambda obj: [e.value for e in obj])


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UUIDPKMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
