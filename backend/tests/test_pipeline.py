"""Tests the DB-writing glue in app/services/pipeline.py. Mocks run_agent (so no
Gemini key is needed) but exercises real Postgres writes — status transitions,
LeadSource creation, the hot/warm-only email-drafting gate, etc."""

from unittest.mock import AsyncMock

import pytest

from app.agents.schemas import GeneratedEmail, LeadScoreResult, ResearchExtraction, SourcedField
from app.core.config import settings
from app.models.campaigns import Campaign, EmailQueueStatus
from app.models.core import CompanyProfile, Organisation
from app.models.leads import Lead, LeadClassification, LeadStatus, ResearchReport
from app.services import pipeline


@pytest.fixture(autouse=True)
def fake_gemini_key(monkeypatch):
    # Building an Agent object constructs a Gemini model instance (needs a key
    # string, no network call); run_agent itself — the part that would actually
    # call the API — is mocked per-test below.
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "fake-test-key")


@pytest.fixture()
def org_and_lead(db_session):
    org = Organisation(name="Haki Systems")
    db_session.add(org)
    db_session.flush()

    profile = CompanyProfile(
        organisation_id=org.id,
        company_name="Haki Systems",
        website="https://hakisystems.co.zw",
        services=["AI automation", "website development"],
        target_industries=["hospitality"],
        phone_numbers=["+263 78 928 7766"],
    )
    db_session.add(profile)

    lead = Lead(
        organisation_id=org.id,
        business_name="Example Hotel",
        website="https://example-hotel.co.zw",
        industry="hospitality",
    )
    db_session.add(lead)
    db_session.commit()
    return org, lead, profile


@pytest.mark.asyncio
async def test_research_lead_persists_report_and_sources(db_session, org_and_lead, monkeypatch):
    org, lead, _ = org_and_lead

    extraction = ResearchExtraction(
        business_description="A boutique hotel in Harare.",
        business_emails=[SourcedField(value="info@example-hotel.co.zw", source_url="https://example-hotel.co.zw/contact")],
        identified_opportunity="No online booking system visible.",
        recommended_service="website_development",
        crawled_urls=["https://example-hotel.co.zw", "https://example-hotel.co.zw/contact"],
    )
    monkeypatch.setattr(pipeline, "run_agent", AsyncMock(return_value=extraction))

    report = await pipeline.research_lead(db_session, lead)

    assert report.summary == "A boutique hotel in Harare."
    assert lead.status == LeadStatus.RESEARCHED
    assert lead.business_email == "info@example-hotel.co.zw"

    sources = db_session.query(pipeline.LeadSource).filter_by(lead_id=lead.id).all()
    assert len(sources) == 1
    assert sources[0].source_url == "https://example-hotel.co.zw/contact"


@pytest.mark.asyncio
async def test_qualify_lead_requires_research_first(db_session, org_and_lead):
    _, lead, profile = org_and_lead
    with pytest.raises(pipeline.PipelineError, match="not been researched"):
        await pipeline.qualify_lead(db_session, lead, profile)


@pytest.mark.asyncio
async def test_qualify_lead_persists_score(db_session, org_and_lead, monkeypatch):
    org, lead, profile = org_and_lead
    db_session.add(ResearchReport(lead_id=lead.id, extracted_data={}, summary="x"))
    db_session.commit()

    score_result = LeadScoreResult(score=82, classification="hot", explanation="Strong fit.")
    monkeypatch.setattr(pipeline, "run_agent", AsyncMock(return_value=score_result))

    score = await pipeline.qualify_lead(db_session, lead, profile)

    assert score.score == 82
    assert score.classification == LeadClassification.HOT
    assert lead.status == LeadStatus.QUALIFIED


@pytest.mark.asyncio
async def test_draft_email_requires_qualification_first(db_session, org_and_lead):
    org, lead, profile = org_and_lead
    campaign = Campaign(organisation_id=org.id, name="Test campaign")
    db_session.add(campaign)
    db_session.commit()

    with pytest.raises(pipeline.PipelineError, match="not been qualified"):
        await pipeline.draft_email_for_lead(db_session, lead, profile, campaign.id)


@pytest.mark.asyncio
async def test_draft_email_blocks_cold_leads(db_session, org_and_lead):
    from app.models.leads import LeadScore

    org, lead, profile = org_and_lead
    campaign = Campaign(organisation_id=org.id, name="Test campaign")
    db_session.add(campaign)
    db_session.add(LeadScore(lead_id=lead.id, score=20, classification=LeadClassification.COLD, explanation="Weak fit."))
    db_session.commit()

    with pytest.raises(pipeline.PipelineError, match="only hot/warm"):
        await pipeline.draft_email_for_lead(db_session, lead, profile, campaign.id)


@pytest.mark.asyncio
async def test_draft_email_persists_queue_item_for_warm_lead(db_session, org_and_lead, monkeypatch):
    from app.models.leads import LeadScore

    org, lead, profile = org_and_lead
    campaign = Campaign(organisation_id=org.id, name="Test campaign")
    db_session.add(campaign)
    db_session.add(LeadScore(lead_id=lead.id, score=65, classification=LeadClassification.WARM, explanation="Plausible fit."))
    db_session.commit()

    generated = GeneratedEmail(
        subject="An opportunity for Example Hotel",
        body="Hello...",
        template_category="website_development",
    )
    monkeypatch.setattr(pipeline, "run_agent", AsyncMock(return_value=generated))

    item = await pipeline.draft_email_for_lead(db_session, lead, profile, campaign.id)

    assert item.status == EmailQueueStatus.AWAITING_APPROVAL
    assert item.subject == "An opportunity for Example Hotel"
    assert lead.status == LeadStatus.DRAFT_READY
