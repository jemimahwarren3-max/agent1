import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.core import User, UserRole
from app.models.leads import Lead, SuppressionListEntry
from app.schemas.lead import LeadCreate, LeadResponse, LeadUpdate
from app.services.audit import log_action

router = APIRouter(prefix="/api/leads", tags=["leads"])

_MANAGE = require_role(UserRole.ADMIN, UserRole.MANAGER)


@router.get("", response_model=list[LeadResponse])
def list_leads(
    status: str | None = Query(default=None),
    industry: str | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Lead).filter(Lead.organisation_id == current_user.organisation_id)
    if status:
        query = query.filter(Lead.status == status)
    if industry:
        query = query.filter(Lead.industry == industry)
    if search:
        query = query.filter(Lead.business_name.ilike(f"%{search}%"))
    return query.order_by(Lead.created_at.desc()).offset(offset).limit(limit).all()


@router.post("", response_model=LeadResponse, status_code=201)
def create_lead(
    payload: LeadCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    is_suppressed = (
        payload.business_email
        and db.query(SuppressionListEntry)
        .filter(
            SuppressionListEntry.organisation_id == current_user.organisation_id,
            SuppressionListEntry.email == payload.business_email,
        )
        .first()
        is not None
    )

    lead = Lead(organisation_id=current_user.organisation_id, **payload.model_dump())
    if is_suppressed:
        lead.is_unsubscribed = True

    db.add(lead)
    db.commit()
    db.refresh(lead)

    log_action(db, current_user.organisation_id, current_user.id, "create", "lead", str(lead.id))
    return lead


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(
    lead_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lead = (
        db.query(Lead)
        .filter(Lead.id == lead_id, Lead.organisation_id == current_user.organisation_id)
        .first()
    )
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.patch("/{lead_id}", response_model=LeadResponse)
def update_lead(
    lead_id: uuid.UUID,
    payload: LeadUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lead = (
        db.query(Lead)
        .filter(Lead.id == lead_id, Lead.organisation_id == current_user.organisation_id)
        .first()
    )
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(lead, field, value)

    db.commit()
    db.refresh(lead)

    log_action(db, current_user.organisation_id, current_user.id, "update", "lead", str(lead.id), updates)
    return lead


@router.delete("/{lead_id}", status_code=204)
def delete_lead(
    lead_id: uuid.UUID,
    current_user: User = Depends(_MANAGE),
    db: Session = Depends(get_db),
):
    lead = (
        db.query(Lead)
        .filter(Lead.id == lead_id, Lead.organisation_id == current_user.organisation_id)
        .first()
    )
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    db.delete(lead)
    db.commit()

    log_action(db, current_user.organisation_id, current_user.id, "delete", "lead", str(lead_id))
