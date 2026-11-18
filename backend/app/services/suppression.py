"""Single place that answers "is this email suppressed for this org" — used at
every point an email could otherwise go out, so the check can't drift out of
sync between lead creation, drafting, and sending."""

import uuid

from sqlalchemy.orm import Session

from app.models.leads import SuppressionListEntry


def is_suppressed(db: Session, organisation_id: uuid.UUID, email: str | None) -> bool:
    if not email:
        return False
    return (
        db.query(SuppressionListEntry)
        .filter(SuppressionListEntry.organisation_id == organisation_id, SuppressionListEntry.email == email)
        .first()
        is not None
    )
