"""Minimal campaign CRUD — enough to give email drafts a campaign_id to belong
to. The full builder (lead filters, templates, schedule, approval UI) is Phase 6."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.campaigns import Campaign
from app.models.core import User
from app.schemas.campaign import CampaignCreate, CampaignResponse

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


@router.get("", response_model=list[CampaignResponse])
def list_campaigns(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(Campaign)
        .filter(Campaign.organisation_id == current_user.organisation_id)
        .order_by(Campaign.created_at.desc())
        .all()
    )


@router.post("", response_model=CampaignResponse, status_code=201)
def create_campaign(
    payload: CampaignCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    campaign = Campaign(organisation_id=current_user.organisation_id, **payload.model_dump())
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


@router.get("/{campaign_id}", response_model=CampaignResponse)
def get_campaign(
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
    return campaign
