import uuid

from pydantic import BaseModel, ConfigDict


class CampaignCreate(BaseModel):
    name: str
    target_country: str | None = None
    target_city: str | None = None
    target_industry: str | None = None


class CampaignResponse(BaseModel):
    id: uuid.UUID
    name: str
    target_country: str | None
    target_city: str | None
    target_industry: str | None
    stage: str
    approval_mode: str

    model_config = ConfigDict(from_attributes=True)
