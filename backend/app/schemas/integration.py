import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class IntegrationResponse(BaseModel):
    id: uuid.UUID
    provider: str
    status: str
    connected_account_email: str | None
    scopes: list[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuthorizeUrlResponse(BaseModel):
    authorize_url: str
