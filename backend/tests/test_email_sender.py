import datetime
from unittest.mock import MagicMock

import pytest

from app.models.campaigns import Campaign, EmailLog, EmailQueueItem, EmailQueueStatus
from app.models.core import Organisation
from app.models.integrations import Integration, IntegrationProvider, IntegrationStatus
from app.models.leads import Lead, LeadStatus
from app.services import email_sender


@pytest.fixture()
def campaign_and_lead(db_session):
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

    lead = Lead(
        organisation_id=org.id,
        business_name="Example Hotel",
        website="https://example-hotel.co.zw",
        business_email="owner@example-hotel.co.zw",
    )
    db_session.add(lead)
    db_session.commit()
    return campaign, lead


@pytest.fixture()
def approved_email_item(db_session, campaign_and_lead):
    campaign, lead = campaign_and_lead
    item = EmailQueueItem(
        campaign_id=campaign.id,
        lead_id=lead.id,
        subject="An idea for Example Hotel",
        body="Hello...",
        status=EmailQueueStatus.APPROVED,
    )
    db_session.add(item)
    db_session.commit()
    return item


@pytest.fixture(autouse=True)
def mocked_credentials(monkeypatch):
    monkeypatch.setattr(email_sender, "get_valid_credentials", lambda db, integration: MagicMock())


def test_send_queued_email_rejects_non_approved(db_session, campaign_and_lead):
    campaign, lead = campaign_and_lead
    item = EmailQueueItem(
        campaign_id=campaign.id, lead_id=lead.id, subject="x", body="y", status=EmailQueueStatus.DRAFT
    )
    db_session.add(item)
    db_session.commit()

    with pytest.raises(email_sender.EmailSendError, match="must be approved"):
        email_sender.send_queued_email(db_session, item)


def test_send_queued_email_rejects_unsubscribed_lead(db_session, campaign_and_lead, approved_email_item):
    _, lead = campaign_and_lead
    lead.is_unsubscribed = True
    db_session.commit()

    with pytest.raises(email_sender.EmailSendError, match="unsubscribed"):
        email_sender.send_queued_email(db_session, approved_email_item)


def test_send_queued_email_success_logs_and_schedules_followup(
    db_session, campaign_and_lead, approved_email_item, monkeypatch
):
    campaign, lead = campaign_and_lead
    monkeypatch.setattr(
        email_sender.gmail_service, "send_email", lambda *a, **k: {"id": "msg-1", "threadId": "thread-1"}
    )

    log = email_sender.send_queued_email(db_session, approved_email_item)

    assert log.gmail_message_id == "msg-1"
    assert log.gmail_thread_id == "thread-1"
    assert log.send_status == "sent"
    assert approved_email_item.status == EmailQueueStatus.SENT
    assert lead.status == LeadStatus.SENT
    assert lead.last_contact_at == datetime.date.today()
    assert lead.next_follow_up_at == datetime.date.today() + datetime.timedelta(
        days=campaign.follow_up_interval_days
    )


def test_send_queued_email_failure_marks_failed(db_session, approved_email_item, monkeypatch):
    def failing_send(*args, **kwargs):
        raise RuntimeError("Gmail API error")

    monkeypatch.setattr(email_sender.gmail_service, "send_email", failing_send)

    with pytest.raises(email_sender.EmailSendError, match="Gmail API error"):
        email_sender.send_queued_email(db_session, approved_email_item)

    assert approved_email_item.status == EmailQueueStatus.FAILED
    log = db_session.query(EmailLog).filter_by(email_queue_id=approved_email_item.id).first()
    assert log.send_status == "failed"
