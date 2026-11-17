import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.schemas import ReplyClassificationResult
from app.core.config import settings
from app.models.campaigns import Campaign, EmailLog, EmailQueueItem, EmailReply, FollowUpTask, ReplyClassification
from app.models.core import Organisation
from app.models.integrations import Integration, IntegrationProvider, IntegrationStatus
from app.models.leads import Lead, LeadStatus, SuppressionListEntry
from app.services import reply_monitor


@pytest.fixture(autouse=True)
def fake_gemini_key(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "fake-test-key")


@pytest.fixture(autouse=True)
def mocked_credentials(monkeypatch):
    monkeypatch.setattr(reply_monitor, "get_valid_credentials", lambda db, integration: MagicMock())


@pytest.fixture()
def campaign_with_sent_email(db_session):
    org = Organisation(name="Haki Systems")
    db_session.add(org)
    db_session.flush()

    integration = Integration(
        organisation_id=org.id,
        provider=IntegrationProvider.GOOGLE_WORKSPACE,
        status=IntegrationStatus.CONNECTED,
        connected_account_email="sales@hakisystems.co.zw",
    )
    db_session.add(integration)
    db_session.flush()

    campaign = Campaign(organisation_id=org.id, name="Test campaign", integration_id=integration.id)
    db_session.add(campaign)

    lead = Lead(organisation_id=org.id, business_name="Example Hotel", website="https://example-hotel.co.zw")
    db_session.add(lead)
    db_session.flush()

    item = EmailQueueItem(campaign_id=campaign.id, lead_id=lead.id, subject="Hi", body="Hi")
    db_session.add(item)
    db_session.flush()

    log = EmailLog(email_queue_id=item.id, gmail_thread_id="thread-1", gmail_message_id="msg-1", send_status="sent")
    db_session.add(log)
    db_session.add(
        FollowUpTask(campaign_id=campaign.id, lead_id=lead.id, scheduled_for=datetime.date(2099, 1, 1))
    )
    db_session.commit()
    return campaign, lead


def _mock_thread_messages(monkeypatch, messages, our_email="sales@hakisystems.co.zw"):
    monkeypatch.setattr(reply_monitor.gmail_service, "list_thread_messages", lambda creds, thread_id: messages)
    monkeypatch.setattr(
        reply_monitor.gmail_service, "is_from_us", lambda message, email: message.get("_from_us", False)
    )
    monkeypatch.setattr(reply_monitor.gmail_service, "extract_message_text", lambda message: message["_text"])


@pytest.mark.asyncio
async def test_sync_replies_skips_our_own_messages(db_session, campaign_with_sent_email, monkeypatch):
    campaign, lead = campaign_with_sent_email
    _mock_thread_messages(monkeypatch, [{"id": "msg-1", "_from_us": True, "_text": "our outbound email"}])

    created = await reply_monitor.sync_replies_for_campaign(db_session, campaign)

    assert created == []


@pytest.mark.asyncio
async def test_sync_replies_classifies_new_reply_and_updates_lead(db_session, campaign_with_sent_email, monkeypatch):
    campaign, lead = campaign_with_sent_email
    _mock_thread_messages(monkeypatch, [{"id": "msg-2", "_from_us": False, "_text": "Yes, let's talk"}])
    monkeypatch.setattr(
        reply_monitor,
        "run_agent",
        AsyncMock(return_value=ReplyClassificationResult(classification="wants_meeting", summary="They want a call.")),
    )

    created = await reply_monitor.sync_replies_for_campaign(db_session, campaign)

    assert len(created) == 1
    assert created[0].classification.value == "wants_meeting"
    assert lead.status == LeadStatus.MEETING_REQUESTED

    # Pending follow-up tasks are cancelled once a real reply comes in.
    task = db_session.query(FollowUpTask).filter_by(lead_id=lead.id).first()
    assert task.is_cancelled is True


@pytest.mark.asyncio
async def test_sync_replies_unsubscribe_suppresses_lead(db_session, campaign_with_sent_email, monkeypatch):
    campaign, lead = campaign_with_sent_email
    lead.business_email = "owner@example-hotel.co.zw"
    db_session.commit()

    _mock_thread_messages(monkeypatch, [{"id": "msg-3", "_from_us": False, "_text": "STOP emailing me"}])
    monkeypatch.setattr(
        reply_monitor,
        "run_agent",
        AsyncMock(return_value=ReplyClassificationResult(classification="unsubscribe", summary="Asked to stop.")),
    )

    await reply_monitor.sync_replies_for_campaign(db_session, campaign)

    assert lead.is_unsubscribed is True
    suppressed = (
        db_session.query(SuppressionListEntry)
        .filter_by(organisation_id=lead.organisation_id, email="owner@example-hotel.co.zw")
        .first()
    )
    assert suppressed is not None


@pytest.mark.asyncio
async def test_sync_replies_is_idempotent_for_already_seen_messages(db_session, campaign_with_sent_email, monkeypatch):
    campaign, lead = campaign_with_sent_email
    db_session.add(
        EmailReply(
            lead_id=lead.id,
            gmail_thread_id="thread-1",
            gmail_message_id="msg-2",
            classification=ReplyClassification.WANTS_MEETING,
        )
    )
    db_session.commit()

    _mock_thread_messages(monkeypatch, [{"id": "msg-2", "_from_us": False, "_text": "Yes, let's talk"}])
    run_agent_mock = AsyncMock()
    monkeypatch.setattr(reply_monitor, "run_agent", run_agent_mock)

    created = await reply_monitor.sync_replies_for_campaign(db_session, campaign)

    assert created == []
    run_agent_mock.assert_not_called()
