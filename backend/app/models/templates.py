import uuid
import enum

from sqlalchemy import String, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.mixins import UUIDPKMixin, TimestampMixin, str_enum


class TemplateCategory(str, enum.Enum):
    GENERAL_INTRODUCTION = "general_introduction"
    WEBSITE_DEVELOPMENT = "website_development"
    AI_AUTOMATION = "ai_automation"
    AI_CUSTOMER_SUPPORT = "ai_customer_support"
    WORKFLOW_AUTOMATION = "workflow_automation"
    CUSTOM_SOFTWARE = "custom_software"
    INDUSTRY_SPECIFIC = "industry_specific"
    FOLLOW_UP = "follow_up"


class EmailTemplate(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "email_templates"

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[TemplateCategory] = mapped_column(
        str_enum(TemplateCategory, "template_category"), nullable=False
    )
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(String(8000), nullable=False)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
