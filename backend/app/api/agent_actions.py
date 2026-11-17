import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.core import CompanyProfile, User
from app.models.leads import Lead
from app.schemas.agent_actions import (
    DraftEmailRequest,
    EmailQueueItemResponse,
    LeadScoreResponse,
    ResearchReportResponse,
)
from app.services.gemini_model import GeminiNotConfiguredError
from app.services.pipeline import PipelineError, draft_email_for_lead, qualify_lead, research_lead

router = APIRouter(prefix="/api/leads", tags=["agent-actions"])


def _get_owned_lead(lead_id: uuid.UUID, user: User, db: Session) -> Lead:
    lead = db.query(Lead).filter(Lead.id == lead_id, Lead.organisation_id == user.organisation_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


def _get_company_profile(user: User, db: Session) -> CompanyProfile:
    profile = (
        db.query(CompanyProfile).filter(CompanyProfile.organisation_id == user.organisation_id).first()
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Company profile not found")
    return profile


@router.post("/{lead_id}/research", response_model=ResearchReportResponse)
async def research_lead_endpoint(
    lead_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    lead = _get_owned_lead(lead_id, current_user, db)
    try:
        return await research_lead(db, lead)
    except GeminiNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.post("/{lead_id}/qualify", response_model=LeadScoreResponse)
async def qualify_lead_endpoint(
    lead_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    lead = _get_owned_lead(lead_id, current_user, db)
    profile = _get_company_profile(current_user, db)
    try:
        return await qualify_lead(db, lead, profile)
    except GeminiNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except PipelineError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{lead_id}/draft-email", response_model=EmailQueueItemResponse)
async def draft_email_endpoint(
    lead_id: uuid.UUID,
    payload: DraftEmailRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lead = _get_owned_lead(lead_id, current_user, db)
    profile = _get_company_profile(current_user, db)
    try:
        return await draft_email_for_lead(db, lead, profile, payload.campaign_id)
    except GeminiNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except PipelineError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
