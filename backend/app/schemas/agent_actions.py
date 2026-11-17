import uuid

from pydantic import BaseModel, ConfigDict


class ResearchReportResponse(BaseModel):
    id: uuid.UUID
    crawled_urls: list[str]
    summary: str | None
    extracted_data: dict

    model_config = ConfigDict(from_attributes=True)


class LeadScoreResponse(BaseModel):
    id: uuid.UUID
    score: float
    classification: str
    explanation: str

    model_config = ConfigDict(from_attributes=True)


class EmailQueueItemResponse(BaseModel):
    id: uuid.UUID
    campaign_id: uuid.UUID
    lead_id: uuid.UUID
    subject: str
    body: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class DraftEmailRequest(BaseModel):
    campaign_id: uuid.UUID
