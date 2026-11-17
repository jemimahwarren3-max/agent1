"""CRUD for email templates. Templates start unapproved; an admin flips
is_approved before the email agent's drafts (gated to hot/warm leads) are
allowed to reuse one as a starting point."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.core import User
from app.models.templates import EmailTemplate, TemplateCategory
from app.schemas.template import TemplateCreate, TemplateResponse, TemplateUpdate

router = APIRouter(prefix="/api/templates", tags=["templates"])


def _get_owned_template(template_id: uuid.UUID, user: User, db: Session) -> EmailTemplate:
    template = (
        db.query(EmailTemplate)
        .filter(EmailTemplate.id == template_id, EmailTemplate.organisation_id == user.organisation_id)
        .first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


def _validate_category(category: str) -> TemplateCategory:
    try:
        return TemplateCategory(category)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Must be one of: {', '.join(c.value for c in TemplateCategory)}",
        )


@router.get("", response_model=list[TemplateResponse])
def list_templates(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(EmailTemplate)
        .filter(EmailTemplate.organisation_id == current_user.organisation_id)
        .order_by(EmailTemplate.created_at.desc())
        .all()
    )


@router.post("", response_model=TemplateResponse, status_code=201)
def create_template(
    payload: TemplateCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    category = _validate_category(payload.category)
    template = EmailTemplate(
        organisation_id=current_user.organisation_id,
        name=payload.name,
        category=category,
        subject=payload.subject,
        body=payload.body,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.get("/{template_id}", response_model=TemplateResponse)
def get_template(
    template_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_owned_template(template_id, current_user, db)


@router.put("/{template_id}", response_model=TemplateResponse)
def update_template(
    template_id: uuid.UUID,
    payload: TemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    template = _get_owned_template(template_id, current_user, db)
    updates = payload.model_dump(exclude_unset=True)
    if "category" in updates:
        updates["category"] = _validate_category(updates["category"])
    for field, value in updates.items():
        setattr(template, field, value)
    db.commit()
    db.refresh(template)
    return template


@router.delete("/{template_id}", status_code=204)
def delete_template(
    template_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    template = _get_owned_template(template_id, current_user, db)
    db.delete(template)
    db.commit()
