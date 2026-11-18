import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.campaigns import Campaign, FollowUpTask
from app.models.core import CompanyProfile, User, UserRole
from app.models.leads import Lead
from app.schemas.agent_actions import EmailQueueItemResponse
from app.schemas.followup import FollowUpTaskResponse
from app.services.audit import log_action
from app.services.followup_service import FollowUpError, generate_follow_up_draft
from app.services.gemini_model import GeminiNotConfiguredError

router = APIRouter(prefix="/api/follow-ups", tags=["follow-ups"])

_MANAGE = require_role(UserRole.ADMIN, UserRole.MANAGER)


def _get_owned_task(task_id: uuid.UUID, user: User, db: Session) -> FollowUpTask:
    task = (
        db.query(FollowUpTask)
        .join(Campaign, FollowUpTask.campaign_id == Campaign.id)
        .filter(FollowUpTask.id == task_id, Campaign.organisation_id == user.organisation_id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Follow-up task not found")
    return task


@router.get("", response_model=list[FollowUpTaskResponse])
def list_follow_ups(
    due_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = (
        db.query(FollowUpTask)
        .join(Campaign, FollowUpTask.campaign_id == Campaign.id)
        .filter(Campaign.organisation_id == current_user.organisation_id)
    )
    if due_only:
        query = query.filter(
            FollowUpTask.is_sent == False,  # noqa: E712
            FollowUpTask.is_cancelled == False,  # noqa: E712
            FollowUpTask.scheduled_for <= datetime.date.today(),
        )
    return query.order_by(FollowUpTask.scheduled_for.asc()).all()


@router.post("/{task_id}/generate-draft", response_model=EmailQueueItemResponse)
async def generate_draft(
    task_id: uuid.UUID,
    current_user: User = Depends(_MANAGE),
    db: Session = Depends(get_db),
):
    task = _get_owned_task(task_id, current_user, db)
    lead = db.get(Lead, task.lead_id)
    profile = (
        db.query(CompanyProfile)
        .filter(CompanyProfile.organisation_id == current_user.organisation_id)
        .first()
    )
    if not lead or not profile:
        raise HTTPException(status_code=404, detail="Lead or company profile not found")

    try:
        item = await generate_follow_up_draft(db, task, lead, profile)
    except FollowUpError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except GeminiNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    log_action(
        db, current_user.organisation_id, current_user.id, "generate_draft", "follow_up_task", str(task.id)
    )
    return item


@router.post("/{task_id}/cancel", response_model=FollowUpTaskResponse)
def cancel_follow_up(
    task_id: uuid.UUID,
    current_user: User = Depends(_MANAGE),
    db: Session = Depends(get_db),
):
    task = _get_owned_task(task_id, current_user, db)
    task.is_cancelled = True
    db.commit()
    db.refresh(task)

    log_action(db, current_user.organisation_id, current_user.id, "cancel", "follow_up_task", str(task.id))
    return task
