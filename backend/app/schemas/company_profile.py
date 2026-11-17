import uuid

from pydantic import BaseModel, ConfigDict


class CompanyProfileUpdate(BaseModel):
    company_name: str | None = None
    website: str | None = None
    description: str | None = None
    phone_numbers: list[str] | None = None
    services: list[str] | None = None
    target_industries: list[str] | None = None
    target_markets: list[str] | None = None
    outreach_messaging_notes: str | None = None


class CompanyProfileResponse(BaseModel):
    id: uuid.UUID
    company_name: str
    website: str
    description: str
    phone_numbers: list[str]
    services: list[str]
    target_industries: list[str]
    target_markets: list[str]
    outreach_messaging_notes: str

    model_config = ConfigDict(from_attributes=True)
