import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EmailReplyResponse(BaseModel):
    id: uuid.UUID
    lead_id: uuid.UUID
    gmail_thread_id: str
    body_snippet: str | None
    classification: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
