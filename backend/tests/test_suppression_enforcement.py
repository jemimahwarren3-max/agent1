"""End-to-end suppression checks: drafting an email for an unsubscribed lead,
and matching suppressed leads into a campaign."""

from unittest.mock import AsyncMock

import pytest

from app.agents.schemas import GeneratedEmail
from app.core.config import settings
from app.models.campaigns import Campaign
from app.models.core import CompanyProfile, Organisation
from app.models.leads import Lead, LeadClassification, LeadScore, LeadStatus, SuppressionListEntry
from app.services import pipeline
from app.services.suppression import is_suppressed


@pytest.fixture(autouse=True)
def fake_gemini_key(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "fake-test-key")


@pytest.fixture()
def org_and_lead(db_session):
    org = Organisation(name="Haki Systems")
    db_session.add(org)
    db_session.flush()

    profile = CompanyProfile(organisation_id=org.id, company_name="Haki Systems", website="https://hakisystems.co.zw")
    db_session.add(profile)

    lead = Lead(
        organisation_id=org.id,
        business_name="Example Hotel",
        website="https://example-hotel.co.zw",
        business_email="owner@example-hotel.co.zw",
        is_unsubscribed=True,
        status=LeadStatus.QUALIFIED,
    )
    db_session.add(lead)
    db_session.flush()
    db_session.add(LeadScore(lead_id=lead.id, score=80, classification=LeadClassification.HOT, explanation="Strong fit."))

    campaign = Campaign(organisation_id=org.id, name="Test campaign")
    db_session.add(campaign)
    db_session.commit()
    return org, lead, profile, campaign


@pytest.mark.asyncio
async def test_draft_email_refuses_unsubscribed_lead(db_session, org_and_lead):
    org, lead, profile, campaign = org_and_lead
    with pytest.raises(pipeline.PipelineError, match="unsubscribed"):
        await pipeline.draft_email_for_lead(db_session, lead, profile, campaign.id)


@pytest.mark.asyncio
async def test_draft_email_still_works_for_subscribed_hot_lead(db_session, org_and_lead, monkeypatch):
    org, lead, profile, campaign = org_and_lead
    lead.is_unsubscribed = False
    db_session.commit()

    generated = GeneratedEmail(subject="Hi", body="Hello", template_category="general_introduction")
    monkeypatch.setattr(pipeline, "run_agent", AsyncMock(return_value=generated))

    item = await pipeline.draft_email_for_lead(db_session, lead, profile, campaign.id)
    assert item.subject == "Hi"


def test_is_suppressed_true_when_entry_exists(db_session, org_and_lead):
    org, lead, _, _ = org_and_lead
    db_session.add(
        SuppressionListEntry(organisation_id=org.id, email="owner@example-hotel.co.zw", reason="test")
    )
    db_session.commit()

    assert is_suppressed(db_session, org.id, "owner@example-hotel.co.zw") is True
    assert is_suppressed(db_session, org.id, "someone-else@example.com") is False
    assert is_suppressed(db_session, org.id, None) is False


