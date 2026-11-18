"""Campaign builder CRUD plus matching leads into a campaign. The approval
queue and actual sending live in app/api/email_queue.py (Phase 4); this file
is about building the campaign and picking which leads it targets."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.campaigns import ApprovalMode, Campaign, CampaignLead
from app.models.core import User, UserRole
from app.models.leads import Lead
from app.schemas.campaign import CampaignCreate, CampaignResponse, CampaignUpdate, MatchLeadsResponse
from app.schemas.lead import LeadResponse
from app.services.audit import log_action
from app.services.suppression import is_suppressed

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])

_MANAGE = require_role(UserRole.ADMIN, UserRole.MANAGER)


def _validate_approval_mode(value: str) -> ApprovalMode:
    try:
        return ApprovalMode(value)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid approval_mode. Must be one of: {', '.join(m.value for m in ApprovalMode)}",
        )


def _get_owned_campaign(campaign_id: uuid.UUID, user: User, db: Session) -> Campaign:
    campaign = (
        db.query(Campaign)
        .filter(Campaign.id == campaign_id, Campaign.organisation_id == user.organisation_id)
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


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
    current_user: User = Depends(_MANAGE),
    db: Session = Depends(get_db),
):
    data = payload.model_dump()
    data["approval_mode"] = _validate_approval_mode(data["approval_mode"])
    campaign = Campaign(organisation_id=current_user.organisation_id, **data)
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    log_action(db, current_user.organisation_id, current_user.id, "create", "campaign", str(campaign.id))
    return campaign


@router.get("/{campaign_id}", response_model=CampaignResponse)
def get_campaign(
    campaign_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_owned_campaign(campaign_id, current_user, db)


@router.patch("/{campaign_id}", response_model=CampaignResponse)
def update_campaign(
    campaign_id: uuid.UUID,
    payload: CampaignUpdate,
    current_user: User = Depends(_MANAGE),
    db: Session = Depends(get_db),
):
    campaign = _get_owned_campaign(campaign_id, current_user, db)
    updates = payload.model_dump(exclude_unset=True)
    if "approval_mode" in updates:
        updates["approval_mode"] = _validate_approval_mode(updates["approval_mode"])
    for field, value in updates.items():
        setattr(campaign, field, value)
    db.commit()
    db.refresh(campaign)

    audit_details = {k: (v.value if hasattr(v, "value") else v) for k, v in updates.items()}
    log_action(
        db, current_user.organisation_id, current_user.id, "update", "campaign", str(campaign.id), audit_details
    )
    return campaign


@router.post("/{campaign_id}/match-leads", response_model=MatchLeadsResponse)
def match_leads(
    campaign_id: uuid.UUID,
    current_user: User = Depends(_MANAGE),
    db: Session = Depends(get_db),
):
    """Adds every lead matching the campaign's target country/city/industry
    that isn't already in it and isn't suppressed."""
    campaign = _get_owned_campaign(campaign_id, current_user, db)

    query = db.query(Lead).filter(Lead.organisation_id == current_user.organisation_id)
    if campaign.target_country:
        query = query.filter(Lead.country == campaign.target_country)
    if campaign.target_city:
        query = query.filter(Lead.city == campaign.target_city)
    if campaign.target_industry:
        query = query.filter(Lead.industry == campaign.target_industry)

    already_in_campaign = {
        lead_id
        for (lead_id,) in db.query(CampaignLead.lead_id).filter(CampaignLead.campaign_id == campaign.id).all()
    }

    matched_count = 0
    skipped_suppressed_count = 0
    for lead in query.all():
        if lead.id in already_in_campaign:
            continue
        if lead.is_unsubscribed or is_suppressed(db, current_user.organisation_id, lead.business_email):
            skipped_suppressed_count += 1
            continue
        db.add(CampaignLead(campaign_id=campaign.id, lead_id=lead.id))
        matched_count += 1

    db.commit()
    log_action(
        db,
        current_user.organisation_id,
        current_user.id,
        "match_leads",
        "campaign",
        str(campaign.id),
        {"matched_count": matched_count, "skipped_suppressed_count": skipped_suppressed_count},
    )
    return MatchLeadsResponse(matched_count=matched_count, skipped_suppressed_count=skipped_suppressed_count)


@router.get("/{campaign_id}/leads", response_model=list[LeadResponse])
def list_campaign_leads(
    campaign_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    campaign = _get_owned_campaign(campaign_id, current_user, db)
    return (
        db.query(Lead)
        .join(CampaignLead, CampaignLead.lead_id == Lead.id)
        .filter(CampaignLead.campaign_id == campaign.id)
        .all()
    )
