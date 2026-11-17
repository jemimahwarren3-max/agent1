import uuid
import enum

from sqlalchemy import String, ForeignKey, JSON, Integer, Date, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import UUIDPKMixin, TimestampMixin, str_enum


class CampaignStage(str, enum.Enum):
    DRAFT = "draft"
    DISCOVERY = "discovery"
    RESEARCH = "research"
    QUALIFICATION = "qualification"
    EMAIL_GENERATION = "email_generation"
    APPROVAL = "approval"
    SENDING = "sending"
    MONITORING = "monitoring"
    COMPLETED = "completed"
    PAUSED = "paused"


class ApprovalMode(str, enum.Enum):
    MANUAL = "manual"
    AUTOMATIC = "automatic"


class Campaign(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "campaigns"

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lead_filters: Mapped[dict] = mapped_column(JSON, default=dict)
    email_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("email_templates.id"), nullable=True
    )
    integration_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("integrations.id"), nullable=True
    )
    max_daily_sends: Mapped[int] = mapped_column(Integer, default=25, nullable=False)
    follow_up_interval_days: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    approval_mode: Mapped[ApprovalMode] = mapped_column(
        str_enum(ApprovalMode, "approval_mode"), default=ApprovalMode.MANUAL, nullable=False
    )
    stage: Mapped[CampaignStage] = mapped_column(
        str_enum(CampaignStage, "campaign_stage"), default=CampaignStage.DRAFT, nullable=False
    )

    campaign_leads: Mapped[list["CampaignLead"]] = relationship(back_populates="campaign")


class CampaignLead(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "campaign_leads"
    __table_args__ = (UniqueConstraint("campaign_id", "lead_id", name="uq_campaign_lead"),)

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False, index=True
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False, index=True
    )

    campaign: Mapped["Campaign"] = relationship(back_populates="campaign_leads")


class EmailQueueStatus(str, enum.Enum):
    DRAFT = "draft"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"


class EmailQueueItem(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "email_queue"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False, index=True
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False, index=True
    )
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(String(8000), nullable=False)
    status: Mapped[EmailQueueStatus] = mapped_column(
        str_enum(EmailQueueStatus, "email_queue_status"),
        default=EmailQueueStatus.DRAFT,
        nullable=False,
        index=True,
    )
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    rejection_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class EmailLog(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "email_logs"

    email_queue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("email_queue.id"), nullable=False, unique=True
    )
    gmail_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gmail_thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    send_status: Mapped[str] = mapped_column(String(50), nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class ReplyClassification(str, enum.Enum):
    INTERESTED = "interested"
    REQUESTING_INFO = "requesting_info"
    WANTS_MEETING = "wants_meeting"
    NOT_INTERESTED = "not_interested"
    OUT_OF_OFFICE = "out_of_office"
    UNSUBSCRIBE = "unsubscribe"
    OTHER = "other"


class EmailReply(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "email_replies"

    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False, index=True
    )
    gmail_thread_id: Mapped[str] = mapped_column(String(255), nullable=False)
    gmail_message_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    body_snippet: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    classification: Mapped[ReplyClassification] = mapped_column(
        str_enum(ReplyClassification, "reply_classification"), nullable=False
    )


class FollowUpTask(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "follow_up_tasks"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False, index=True
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False, index=True
    )
    scheduled_for: Mapped[Date] = mapped_column(Date, nullable=False)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_cancelled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
