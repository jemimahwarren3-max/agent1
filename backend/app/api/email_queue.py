"""Approve/reject/send on drafted emails. The polished approval-queue UI is
Phase 5 — these endpoints exist now because Gmail sending (Phase 4) needs
something to transition AWAITING_APPROVAL -> APPROVED -> SENT."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.campaigns import Campaign, EmailQueueItem, EmailQueueStatus
from app.models.core import User
from app.schemas.agent_actions import EmailQueueItemResponse
from app.schemas.email_queue import EmailLogResponse, RejectEmailRequest
from app.services.email_sender import EmailSendError, send_queued_email

router = APIRouter(prefix="/api/email-queue", tags=["email-queue"])


def _get_owned_item(item_id: uuid.UUID, user: User, db: Session) -> EmailQueueItem:
    item = (
        db.query(EmailQueueItem)
        .join(Campaign, EmailQueueItem.campaign_id == Campaign.id)
        .filter(EmailQueueItem.id == item_id, Campaign.organisation_id == user.organisation_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Queued email not found")
    return item


@router.get("", response_model=list[EmailQueueItemResponse])
def list_email_queue(
    status: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = (
        db.query(EmailQueueItem)
        .join(Campaign, EmailQueueItem.campaign_id == Campaign.id)
        .filter(Campaign.organisation_id == current_user.organisation_id)
    )
    if status:
        query = query.filter(EmailQueueItem.status == status)
    return query.order_by(EmailQueueItem.created_at.desc()).all()


@router.post("/{item_id}/approve", response_model=EmailQueueItemResponse)
def approve_email(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = _get_owned_item(item_id, current_user, db)
    if item.status != EmailQueueStatus.AWAITING_APPROVAL:
        raise HTTPException(status_code=400, detail=f"Email is '{item.status.value}', not awaiting approval.")
    item.status = EmailQueueStatus.APPROVED
    item.reviewed_by_user_id = current_user.id
    db.commit()
    db.refresh(item)
    return item


@router.post("/{item_id}/reject", response_model=EmailQueueItemResponse)
def reject_email(
    item_id: uuid.UUID,
    payload: RejectEmailRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = _get_owned_item(item_id, current_user, db)
    if item.status != EmailQueueStatus.AWAITING_APPROVAL:
        raise HTTPException(status_code=400, detail=f"Email is '{item.status.value}', not awaiting approval.")
    item.status = EmailQueueStatus.REJECTED
    item.reviewed_by_user_id = current_user.id
    item.rejection_reason = payload.reason
    db.commit()
    db.refresh(item)
    return item


@router.post("/{item_id}/send", response_model=EmailLogResponse)
def send_email(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = _get_owned_item(item_id, current_user, db)
    try:
        return send_queued_email(db, item)
    except EmailSendError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
