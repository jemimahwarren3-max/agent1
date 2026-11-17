"""Exercises the discovery-job orchestrator against a real Postgres, with the
Gemini-backed agent call (run_agent) and the research/qualify pipeline steps
mocked — so dedup, counting, status transitions and pause/cancel are tested for
real without needing a Gemini key."""

from unittest.mock import AsyncMock

import pytest

from app.agents.schemas import DiscoveredBusiness, DiscoveryResult
from app.core.config import settings
from app.models.core import CompanyProfile, Organisation
from app.models.jobs import JobStatus, ScrapingJob
from app.models.leads import Lead, LeadClassification, LeadScore, LeadStatus
from app.services import discovery_job, pipeline


@pytest.fixture(autouse=True)
def fake_gemini_key(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "fake-test-key")


@pytest.fixture()
def org_profile_job(db_session):
    org = Organisation(name="Haki Systems")
    db_session.add(org)
    db_session.flush()
    db_session.add(
        CompanyProfile(
            organisation_id=org.id,
            company_name="Haki Systems",
            website="https://hakisystems.co.zw",
            services=["AI automation"],
            target_industries=["hospitality"],
        )
    )
    job = ScrapingJob(
        organisation_id=org.id,
        search_params={"country": "Zimbabwe", "city": "Harare", "industry": "hospitality"},
        status=JobStatus.RUNNING,
    )
    db_session.add(job)
    db_session.commit()
    return org, job


def _discovery_returning(*websites):
    return DiscoveryResult(
        businesses=[
            DiscoveredBusiness(business_name=f"Biz {i}", website=w, discovery_source="https://search")
            for i, w in enumerate(websites)
        ],
        search_queries_used=["q"],
    )


@pytest.mark.asyncio
async def test_discovery_phase_dedupes_and_counts(db_session, org_profile_job, monkeypatch):
    org, job = org_profile_job
    # Two of these collapse to the same domain (www + path); one is a true dup.
    monkeypatch.setattr(
        discovery_job,
        "run_agent",
        AsyncMock(
            return_value=_discovery_returning(
                "https://hotel-a.co.zw",
                "https://www.hotel-a.co.zw/contact",  # same domain as above -> duplicate
                "https://hotel-b.co.zw",
            )
        ),
    )

    await discovery_job._discovery_phase(db_session, job)

    leads = db_session.query(Lead).filter(Lead.scraping_job_id == job.id).all()
    assert job.discovered_count == 2
    assert job.duplicate_count == 1
    assert len(leads) == 2
    assert all(l.status == LeadStatus.NEW for l in leads)
    assert all(l.city == "Harare" for l in leads)


@pytest.mark.asyncio
async def test_discovery_phase_skips_preexisting_org_leads(db_session, org_profile_job, monkeypatch):
    org, job = org_profile_job
    db_session.add(
        Lead(organisation_id=org.id, business_name="Existing", website="https://hotel-a.co.zw")
    )
    db_session.commit()

    monkeypatch.setattr(
        discovery_job, "run_agent", AsyncMock(return_value=_discovery_returning("https://hotel-a.co.zw"))
    )
    await discovery_job._discovery_phase(db_session, job)

    assert job.discovered_count == 0
    assert job.duplicate_count == 1


@pytest.mark.asyncio
async def test_research_phase_processes_new_leads_and_counts_qualified(
    db_session, org_profile_job, monkeypatch
):
    org, job = org_profile_job
    profile = db_session.query(CompanyProfile).filter_by(organisation_id=org.id).first()

    for w in ["https://a.co.zw", "https://b.co.zw"]:
        db_session.add(
            Lead(organisation_id=org.id, scraping_job_id=job.id, business_name="X", website=w, status=LeadStatus.NEW)
        )
    db_session.commit()

    async def fake_research(db, lead):
        lead.status = LeadStatus.RESEARCHED
        db.commit()

    classifications = iter([LeadClassification.HOT, LeadClassification.COLD])

    async def fake_qualify(db, lead, prof):
        lead.status = LeadStatus.QUALIFIED
        score = LeadScore(lead_id=lead.id, score=50, classification=next(classifications), explanation="x")
        db.add(score)
        db.commit()
        return score

    monkeypatch.setattr(pipeline, "research_lead", fake_research)
    monkeypatch.setattr(pipeline, "qualify_lead", fake_qualify)

    stop = await discovery_job._research_phase(db_session, job, profile)

    assert stop is None
    assert job.researched_count == 2
    assert job.qualified_count == 1  # only the HOT one counts


@pytest.mark.asyncio
async def test_research_phase_stops_when_cancelled(db_session, org_profile_job, monkeypatch):
    org, job = org_profile_job
    profile = db_session.query(CompanyProfile).filter_by(organisation_id=org.id).first()
    db_session.add(
        Lead(organisation_id=org.id, scraping_job_id=job.id, business_name="X", website="https://a.co.zw", status=LeadStatus.NEW)
    )
    db_session.commit()

    # Simulate an API cancel landing before the first business is processed.
    async def fake_research(db, lead):
        raise AssertionError("should not be called once cancelled")

    monkeypatch.setattr(pipeline, "research_lead", fake_research)
    job.status = JobStatus.CANCELLED
    db_session.commit()

    stop = await discovery_job._research_phase(db_session, job, profile)
    assert stop == "cancelled"
    assert job.researched_count == 0


@pytest.mark.asyncio
async def test_research_phase_records_failure_and_continues(db_session, org_profile_job, monkeypatch):
    org, job = org_profile_job
    profile = db_session.query(CompanyProfile).filter_by(organisation_id=org.id).first()
    db_session.add(
        Lead(organisation_id=org.id, scraping_job_id=job.id, business_name="X", website="https://a.co.zw", status=LeadStatus.NEW)
    )
    db_session.commit()

    async def fake_research(db, lead):
        raise RuntimeError("crawl blocked by robots.txt")

    monkeypatch.setattr(pipeline, "research_lead", fake_research)

    stop = await discovery_job._research_phase(db_session, job, profile)

    assert stop is None
    assert job.failed_count == 1
    lead = db_session.query(Lead).filter(Lead.scraping_job_id == job.id).first()
    assert lead.status == LeadStatus.ARCHIVED
    assert "robots.txt" in lead.research_notes


@pytest.mark.asyncio
async def test_full_run_via_sessionlocal(db_session, org_profile_job, monkeypatch):
    """Drives run_discovery_job end-to-end, pointing its SessionLocal at the test DB."""
    org, job = org_profile_job
    job.status = JobStatus.PENDING
    db_session.commit()

    monkeypatch.setattr(discovery_job, "run_agent", AsyncMock(return_value=_discovery_returning("https://c.co.zw")))

    async def fake_research(db, lead):
        lead.status = LeadStatus.RESEARCHED
        db.commit()

    async def fake_qualify(db, lead, prof):
        lead.status = LeadStatus.QUALIFIED
        s = LeadScore(lead_id=lead.id, score=80, classification=LeadClassification.HOT, explanation="x")
        db.add(s)
        db.commit()
        return s

    monkeypatch.setattr(pipeline, "research_lead", fake_research)
    monkeypatch.setattr(pipeline, "qualify_lead", fake_qualify)

    # run_discovery_job opens its own session; bind that to the test engine. Use a
    # non-closing wrapper so the orchestrator's db.close() doesn't kill the fixture's session.
    bind = db_session.get_bind()
    from sqlalchemy.orm import sessionmaker

    TestSession = sessionmaker(bind=bind)
    monkeypatch.setattr(discovery_job, "SessionLocal", TestSession)

    await discovery_job.run_discovery_job(job.id)

    db_session.expire_all()
    refreshed = db_session.get(ScrapingJob, job.id)
    assert refreshed.status == JobStatus.COMPLETED
    assert refreshed.discovered_count == 1
    assert refreshed.researched_count == 1
    assert refreshed.qualified_count == 1
