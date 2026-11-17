import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class LeadCreate(BaseModel):
    business_name: str
    website: str
    country: str | None = None
    city: str | None = None
    industry: str | None = None
    business_description: str | None = None
    business_email: str | None = None
    phone_number: str | None = None
    contact_person: str | None = None
    contact_person_role: str | None = None


class LeadUpdate(BaseModel):
    business_name: str | None = None
    country: str | None = None
    city: str | None = None
    industry: str | None = None
    business_description: str | None = None
    business_email: str | None = None
    phone_number: str | None = None
    contact_person: str | None = None
    contact_person_role: str | None = None
    identified_opportunity: str | None = None
    recommended_service: str | None = None
    status: str | None = None
    next_follow_up_at: date | None = None


class LeadResponse(BaseModel):
    id: uuid.UUID
    business_name: str
    website: str
    country: str | None
    city: str | None
    industry: str | None
    business_email: str | None
    phone_number: str | None
    contact_person: str | None
    identified_opportunity: str | None
    recommended_service: str | None
    status: str
    is_unsubscribed: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
