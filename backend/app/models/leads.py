import uuid
import enum

from sqlalchemy import String, ForeignKey, JSON, Float, Date, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import UUIDPKMixin, TimestampMixin, str_enum


class LeadStatus(str, enum.Enum):
    NEW = "new"
    RESEARCHED = "researched"
    QUALIFIED = "qualified"
    DRAFT_READY = "draft_ready"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    SENT = "sent"
    REPLIED = "replied"
    INTERESTED = "interested"
    MEETING_REQUESTED = "meeting_requested"
    NOT_INTERESTED = "not_interested"
    UNSUBSCRIBED = "unsubscribed"
    BOUNCED = "bounced"
    ARCHIVED = "archived"


class LeadClassification(str, enum.Enum):
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"
    UNQUALIFIED = "unqualified"


class Lead(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "leads"
    __table_args__ = (UniqueConstraint("organisation_id", "website", name="uq_lead_org_website"),)

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id"), nullable=False, index=True
    )
    scraping_job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scraping_jobs.id"), nullable=True, index=True
    )
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    website: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    business_description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    business_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    contact_person: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_person_role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    identified_opportunity: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    recommended_service: Mapped[str | None] = mapped_column(String(255), nullable=True)
    research_notes: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    status: Mapped[LeadStatus] = mapped_column(
        str_enum(LeadStatus, "lead_status"), default=LeadStatus.NEW, nullable=False, index=True
    )
    last_researched_at: Mapped[Date | None] = mapped_column(Date, nullable=True)
    last_contact_at: Mapped[Date | None] = mapped_column(Date, nullable=True)
    next_follow_up_at: Mapped[Date | None] = mapped_column(Date, nullable=True)
    is_unsubscribed: Mapped[bool] = mapped_column(default=False, nullable=False)

    sources: Mapped[list["LeadSource"]] = relationship(back_populates="lead")
    research_reports: Mapped[list["ResearchReport"]] = relationship(back_populates="lead")
    scores: Mapped[list["LeadScore"]] = relationship(back_populates="lead")


class LeadSource(UUIDPKMixin, TimestampMixin, Base):
    """Where a lead or a specific contact detail was discovered. Required for the
    'never fabricate contact info' rule — every field must be traceable to a source_url."""

    __tablename__ = "lead_sources"

    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False, index=True
    )
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    discovered_via: Mapped[str] = mapped_column(String(100), nullable=False)

    lead: Mapped["Lead"] = relationship(back_populates="sources")


class ResearchReport(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "research_reports"

    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False, index=True
    )
    crawled_urls: Mapped[list] = mapped_column(JSON, default=list)
    extracted_data: Mapped[dict] = mapped_column(JSON, default=dict)
    summary: Mapped[str | None] = mapped_column(String(4000), nullable=True)

    lead: Mapped["Lead"] = relationship(back_populates="research_reports")


class LeadScore(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "lead_scores"

    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False, index=True
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    classification: Mapped[LeadClassification] = mapped_column(
        str_enum(LeadClassification, "lead_classification"), nullable=False
    )
    explanation: Mapped[str] = mapped_column(String(2000), nullable=False)

    lead: Mapped["Lead"] = relationship(back_populates="scores")


class SuppressionListEntry(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "suppression_list"
    __table_args__ = (UniqueConstraint("organisation_id", "email", name="uq_suppression_org_email"),)

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
