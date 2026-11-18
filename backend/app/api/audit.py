from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.db.session import get_db
from app.models.core import AuditLog, User
from app.schemas.audit import AuditLogResponse

router = APIRouter(prefix="/api/audit-logs", tags=["audit"])


@router.get("", response_model=list[AuditLogResponse])
def list_audit_logs(
    limit: int = Query(default=100, le=500),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return (
        db.query(AuditLog)
        .filter(AuditLog.organisation_id == current_user.organisation_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .all()
    )
