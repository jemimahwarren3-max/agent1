import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.core import User
from app.models.jobs import JobStatus, ScrapingJob
from app.schemas.discovery import DiscoveryJobResponse, DiscoveryStartRequest
from app.services.discovery_job import run_discovery_job_sync

router = APIRouter(prefix="/api/discovery", tags=["discovery"])


def _get_owned_job(job_id: uuid.UUID, user: User, db: Session) -> ScrapingJob:
    job = (
        db.query(ScrapingJob)
        .filter(ScrapingJob.id == job_id, ScrapingJob.organisation_id == user.organisation_id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Discovery job not found")
    return job


@router.post("/start", response_model=DiscoveryJobResponse, status_code=201)
def start_discovery(
    payload: DiscoveryStartRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    search_params = payload.model_dump(mode="json", exclude_none=True)
    search_params.pop("campaign_id", None)

    job = ScrapingJob(
        organisation_id=current_user.organisation_id,
        campaign_id=payload.campaign_id,
        search_params=search_params,
        status=JobStatus.PENDING,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(run_discovery_job_sync, job.id)
    return job


@router.get("/jobs", response_model=list[DiscoveryJobResponse])
def list_jobs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(ScrapingJob)
        .filter(ScrapingJob.organisation_id == current_user.organisation_id)
        .order_by(ScrapingJob.created_at.desc())
        .all()
    )


@router.get("/jobs/{job_id}", response_model=DiscoveryJobResponse)
def get_job(
    job_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return _get_owned_job(job_id, current_user, db)


@router.post("/jobs/{job_id}/pause", response_model=DiscoveryJobResponse)
def pause_job(
    job_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    job = _get_owned_job(job_id, current_user, db)
    if job.status not in (JobStatus.RUNNING, JobStatus.PENDING):
        raise HTTPException(status_code=400, detail=f"Cannot pause a job in '{job.status.value}' state")
    job.status = JobStatus.PAUSED
    db.commit()
    db.refresh(job)
    return job


@router.post("/jobs/{job_id}/resume", response_model=DiscoveryJobResponse)
def resume_job(
    job_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = _get_owned_job(job_id, current_user, db)
    if job.status != JobStatus.PAUSED:
        raise HTTPException(status_code=400, detail="Only a paused job can be resumed")
    job.status = JobStatus.RUNNING
    db.commit()
    db.refresh(job)

    background_tasks.add_task(run_discovery_job_sync, job.id)
    return job


@router.post("/jobs/{job_id}/cancel", response_model=DiscoveryJobResponse)
def cancel_job(
    job_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    job = _get_owned_job(job_id, current_user, db)
    if job.status in (JobStatus.COMPLETED, JobStatus.CANCELLED, JobStatus.FAILED):
        raise HTTPException(status_code=400, detail=f"Job already in terminal state '{job.status.value}'")
    job.status = JobStatus.CANCELLED
    db.commit()
    db.refresh(job)
    return job
