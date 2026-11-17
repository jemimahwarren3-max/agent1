import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TemplateCreate(BaseModel):
    name: str
    category: str
    subject: str
    body: str


class TemplateUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    subject: str | None = None
    body: str | None = None
    is_approved: bool | None = None


class TemplateResponse(BaseModel):
    id: uuid.UUID
    name: str
    category: str
    subject: str
    body: str
    is_approved: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
