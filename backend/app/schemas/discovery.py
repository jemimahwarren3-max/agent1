import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DiscoveryStartRequest(BaseModel):
    country: str | None = None
    city: str | None = None
    industry: str | None = None
    business_type: str | None = None
    keywords: str | None = None
    services: str | None = None
    num_leads: int = Field(default=20, ge=1, le=200)
    campaign_id: uuid.UUID | None = None


class DiscoveryJobResponse(BaseModel):
    id: uuid.UUID
    status: str
    search_params: dict
    discovered_count: int
    researched_count: int
    failed_count: int
    duplicate_count: int
    qualified_count: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
