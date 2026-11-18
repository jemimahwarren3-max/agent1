from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.core import CompanyProfile, User
from app.schemas.company_profile import CompanyProfileResponse, CompanyProfileUpdate
from app.services.audit import log_action

router = APIRouter(prefix="/api/company-profile", tags=["company-profile"])


@router.get("", response_model=CompanyProfileResponse)
def get_company_profile(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    profile = (
        db.query(CompanyProfile)
        .filter(CompanyProfile.organisation_id == current_user.organisation_id)
        .first()
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Company profile not found")
    return profile


@router.patch("", response_model=CompanyProfileResponse)
def update_company_profile(
    payload: CompanyProfileUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    profile = (
        db.query(CompanyProfile)
        .filter(CompanyProfile.organisation_id == current_user.organisation_id)
        .first()
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Company profile not found")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)

    log_action(db, current_user.organisation_id, current_user.id, "update", "company_profile", str(profile.id), updates)
    return profile
