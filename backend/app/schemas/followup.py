import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict


class FollowUpTaskResponse(BaseModel):
    id: uuid.UUID
    campaign_id: uuid.UUID
    lead_id: uuid.UUID
    scheduled_for: date
    is_approved: bool
    is_sent: bool
    is_cancelled: bool

    model_config = ConfigDict(from_attributes=True)
