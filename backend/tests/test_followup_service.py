import datetime
from unittest.mock import AsyncMock

import pytest

from app.agents.schemas import GeneratedEmail
from app.core.config import settings
from app.models.campaigns import Campaign, EmailQueueStatus, FollowUpTask
from app.models.core import CompanyProfile, Organisation
from app.models.leads import Lead, LeadStatus
from app.services import followup_service


@pytest.fixture(autouse=True)
def fake_gemini_key(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "fake-test-key")


@pytest.fixture()
def task_lead_and_profile(db_session):
    org = Organisation(name="Haki Systems")
    db_session.add(org)
    db_session.flush()

    profile = CompanyProfile(
        organisation_id=org.id,
        company_name="Haki Systems",
        website="https://hakisystems.co.zw",
        phone_numbers=["+263 78 928 7766"],
    )
    db_session.add(profile)

    campaign = Campaign(organisation_id=org.id, name="Test campaign")
    db_session.add(campaign)

    lead = Lead(organisation_id=org.id, business_name="Example Hotel", website="https://example-hotel.co.zw")
    db_session.add(lead)
    db_session.flush()

    task = FollowUpTask(campaign_id=campaign.id, lead_id=lead.id, scheduled_for=datetime.date.today())
    db_session.add(task)
    db_session.commit()
    return task, lead, profile


@pytest.mark.asyncio
async def test_generate_follow_up_draft_creates_queue_item(db_session, task_lead_and_profile, monkeypatch):
    task, lead, profile = task_lead_and_profile
    generated = GeneratedEmail(subject="Following up", body="Just checking in...", template_category="follow_up")
    monkeypatch.setattr(followup_service, "run_agent", AsyncMock(return_value=generated))

    item = await followup_service.generate_follow_up_draft(db_session, task, lead, profile)

    assert item.status == EmailQueueStatus.AWAITING_APPROVAL
    assert item.subject == "Following up"
    assert lead.status == LeadStatus.DRAFT_READY
    assert task.is_sent is True


@pytest.mark.asyncio
async def test_generate_follow_up_draft_rejects_cancelled_task(db_session, task_lead_and_profile):
    task, lead, profile = task_lead_and_profile
    task.is_cancelled = True
    db_session.commit()

    with pytest.raises(followup_service.FollowUpError):
        await followup_service.generate_follow_up_draft(db_session, task, lead, profile)
