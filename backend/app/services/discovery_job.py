"""Background orchestrator for a discovery job: runs the Discovery agent to find
businesses, dedupes and saves them as leads, then researches and qualifies each.

Pause/resume/cancel are coordinated purely through the job's `status` column in
the DB — the loop re-reads it before each business, so pausing stops cleanly at a
business boundary and resuming picks up the remaining NEW leads. Because leads are
persisted during the discovery phase and the research phase only processes leads
still in NEW status, resuming is naturally idempotent and never re-runs the
(quota-costing) search.

Processing is sequential within a job. Multiple jobs can run concurrently; a
global concurrency cap belongs at the queue/worker layer (Phase 5+), noted here
rather than faked.
"""

import asyncio
import uuid

from sqlalchemy.orm import Session

from app.agents.discovery_agent import build_discovery_agent
from app.agents.runner import run_agent
from app.agents.schemas import DiscoveryResult
from app.db.session import SessionLocal
from app.models.core import CompanyProfile
from app.models.jobs import JobStatus, ScrapingJob
from app.models.leads import Lead, LeadClassification, LeadScore, LeadStatus
from app.services import pipeline
from app.services.agent_logging import track_agent_run
from app.services.url_utils import normalize_domain


def _build_discovery_message(params: dict) -> str:
    lines = ["Find businesses matching this brief:"]
    for label, key in [
        ("Country", "country"),
        ("City/region", "city"),
        ("Industry", "industry"),
        ("Business type", "business_type"),
        ("Keywords", "keywords"),
        ("Services to promote", "services"),
        ("Number of businesses wanted", "num_leads"),
    ]:
        if params.get(key):
            lines.append(f"- {label}: {params[key]}")
    return "\n".join(lines)


def _is_stopped(db: Session, job_id: uuid.UUID) -> str | None:
    """Returns the terminal/paused status if the job should stop, else None.
    Re-queried from the DB so an API pause/cancel is seen mid-run."""
    db.expire_all()
    job = db.get(ScrapingJob, job_id)
    if job is None:
        return "deleted"
    if job.status in (JobStatus.PAUSED, JobStatus.CANCELLED):
        return job.status.value
    return None


async def _discovery_phase(db: Session, job: ScrapingJob) -> None:
    """Runs the Discovery agent once and persists unique businesses as NEW leads.
    Skipped on resume (discovered_count already > 0)."""
    if job.discovered_count > 0:
        return

    agent = build_discovery_agent()
    message = _build_discovery_message(job.search_params or {})

    with track_agent_run(
        db, job.organisation_id, "discovery_agent", job.search_params or {}, scraping_job_id=job.id
    ) as (run, log):
        log("start", "Running discovery search")
        result: DiscoveryResult = await run_agent(agent, message)
        run.output_payload = result.model_dump()
        log("discovery_complete", f"Found {len(result.businesses)} candidates")

    existing_domains = {
        normalize_domain(w)
        for (w,) in db.query(Lead.website).filter(Lead.organisation_id == job.organisation_id).all()
    }

    seen_this_run: set[str] = set()
    for biz in result.businesses:
        domain = normalize_domain(biz.website)
        if not domain or domain in existing_domains or domain in seen_this_run:
            job.duplicate_count += 1
            continue
        seen_this_run.add(domain)
        db.add(
            Lead(
                organisation_id=job.organisation_id,
                scraping_job_id=job.id,
                business_name=biz.business_name,
                website=biz.website,
                country=job.search_params.get("country"),
                city=job.search_params.get("city"),
                industry=job.search_params.get("industry"),
                status=LeadStatus.NEW,
            )
        )
        job.discovered_count += 1
    db.commit()


async def _research_phase(db: Session, job: ScrapingJob, profile: CompanyProfile) -> str | None:
    """Researches + qualifies each still-NEW lead for the job. Returns a stop
    reason ('paused'/'cancelled'/'deleted') if interrupted, else None when done."""
    while True:
        stop = _is_stopped(db, job.id)
        if stop:
            return stop

        lead = (
            db.query(Lead)
            .filter(Lead.scraping_job_id == job.id, Lead.status == LeadStatus.NEW)
            .order_by(Lead.created_at)
            .first()
        )
        if lead is None:
            return None  # all processed

        try:
            await pipeline.research_lead(db, lead)
            job.researched_count += 1

            score = await pipeline.qualify_lead(db, lead, profile)
            if score.classification in (LeadClassification.HOT, LeadClassification.WARM):
                job.qualified_count += 1
        except Exception as exc:  # per-business failure must not kill the whole job
            job.failed_count += 1
            lead.status = LeadStatus.ARCHIVED
            lead.research_notes = f"Discovery job error: {exc}"
        db.commit()


async def run_discovery_job(job_id: uuid.UUID) -> None:
    """Entry point for the background task. Opens its own DB session since the
    request-scoped session is already closed by the time this runs."""
    db = SessionLocal()
    try:
        job = db.get(ScrapingJob, job_id)
        if job is None or job.status == JobStatus.CANCELLED:
            return

        profile = (
            db.query(CompanyProfile)
            .filter(CompanyProfile.organisation_id == job.organisation_id)
            .first()
        )
        if profile is None:
            job.status = JobStatus.FAILED
            job.error_message = "No company profile configured for this organisation."
            db.commit()
            return

        job.status = JobStatus.RUNNING
        db.commit()

        try:
            await _discovery_phase(db, job)
            stop = await _research_phase(db, job, profile)
        except Exception as exc:
            db.rollback()
            job = db.get(ScrapingJob, job_id)
            if job:
                job.status = JobStatus.FAILED
                job.error_message = str(exc)[:1000]
                db.commit()
            return

        job = db.get(ScrapingJob, job_id)
        if job is None:
            return
        if stop == "cancelled":
            job.status = JobStatus.CANCELLED
        elif stop == "paused":
            job.status = JobStatus.PAUSED
        elif stop is None:
            job.status = JobStatus.COMPLETED
        db.commit()
    finally:
        db.close()


def run_discovery_job_sync(job_id: uuid.UUID) -> None:
    """Sync wrapper for FastAPI BackgroundTasks (which runs sync callables in a
    threadpool). Each job gets its own event loop."""
    asyncio.run(run_discovery_job(job_id))
