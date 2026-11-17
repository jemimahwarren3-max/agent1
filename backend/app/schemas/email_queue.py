import uuid

from pydantic import BaseModel, ConfigDict


class RejectEmailRequest(BaseModel):
    reason: str


class EmailLogResponse(BaseModel):
    id: uuid.UUID
    email_queue_id: uuid.UUID
    gmail_message_id: str | None
    gmail_thread_id: str | None
    send_status: str
    error_message: str | None

    model_config = ConfigDict(from_attributes=True)
