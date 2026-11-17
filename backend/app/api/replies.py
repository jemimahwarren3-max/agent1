import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.campaigns import Campaign, EmailReply
from app.models.core import User
from app.models.leads import Lead
from app.schemas.reply import EmailReplyResponse
from app.services.gemini_model import GeminiNotConfiguredError
from app.services.reply_monitor import ReplyMonitorError, sync_replies_for_campaign

router = APIRouter(tags=["replies"])


@router.get("/api/replies", response_model=list[EmailReplyResponse])
def list_replies(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(EmailReply)
        .join(Lead, EmailReply.lead_id == Lead.id)
        .filter(Lead.organisation_id == current_user.organisation_id)
        .order_by(EmailReply.created_at.desc())
        .all()
    )


@router.post("/api/campaigns/{campaign_id}/sync-replies", response_model=list[EmailReplyResponse])
async def sync_replies(
    campaign_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    campaign = (
        db.query(Campaign)
        .filter(Campaign.id == campaign_id, Campaign.organisation_id == current_user.organisation_id)
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    try:
        return await sync_replies_for_campaign(db, campaign)
    except ReplyMonitorError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except GeminiNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
