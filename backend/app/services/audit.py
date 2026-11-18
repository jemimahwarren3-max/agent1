"""One call per mutation to record who did what. Kept as a plain function
(not a decorator/middleware) so each endpoint stays explicit about what it's
logging, matching the rest of this codebase's style."""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.core import AuditLog


def log_action(
    db: Session,
    organisation_id: uuid.UUID,
    actor_user_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditLog(
            organisation_id=organisation_id,
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details or {},
        )
    )
    db.commit()
