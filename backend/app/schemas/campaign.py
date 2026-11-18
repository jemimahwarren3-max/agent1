import uuid

from pydantic import BaseModel, ConfigDict


class CampaignCreate(BaseModel):
    name: str
    target_country: str | None = None
    target_city: str | None = None
    target_industry: str | None = None
    email_template_id: uuid.UUID | None = None
    integration_id: uuid.UUID | None = None
    max_daily_sends: int = 25
    follow_up_interval_days: int = 5
    approval_mode: str = "manual"


class CampaignUpdate(BaseModel):
    name: str | None = None
    target_country: str | None = None
    target_city: str | None = None
    target_industry: str | None = None
    email_template_id: uuid.UUID | None = None
    integration_id: uuid.UUID | None = None
    max_daily_sends: int | None = None
    follow_up_interval_days: int | None = None
    approval_mode: str | None = None


class CampaignResponse(BaseModel):
    id: uuid.UUID
    name: str
    target_country: str | None
    target_city: str | None
    target_industry: str | None
    email_template_id: uuid.UUID | None
    integration_id: uuid.UUID | None
    max_daily_sends: int
    follow_up_interval_days: int
    stage: str
    approval_mode: str

    model_config = ConfigDict(from_attributes=True)


class MatchLeadsResponse(BaseModel):
    matched_count: int
    skipped_suppressed_count: int
