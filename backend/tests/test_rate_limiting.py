from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core import rate_limit
from app.db.session import get_db
from app.main import app
from app.models.campaigns import Campaign, EmailLog, EmailQueueItem, EmailQueueStatus
from app.models.core import Organisation
from app.models.integrations import Integration, IntegrationProvider, IntegrationStatus
from app.models.leads import Lead
from app.services import email_sender


def test_rate_limit_auth_blocks_after_threshold():
    rate_limit.reset()
    request = MagicMock()
    request.client.host = "1.2.3.4"

    for _ in range(rate_limit._MAX_REQUESTS):
        rate_limit.rate_limit_auth(request)

    with pytest.raises(Exception) as exc_info:
        rate_limit.rate_limit_auth(request)
    assert exc_info.value.status_code == 429


def test_rate_limit_auth_tracks_ips_independently():
    rate_limit.reset()
    request_a = MagicMock()
    request_a.client.host = "1.1.1.1"
    request_b = MagicMock()
    request_b.client.host = "2.2.2.2"

    for _ in range(rate_limit._MAX_REQUESTS):
        rate_limit.rate_limit_auth(request_a)

    # Different IP isn't affected by request_a's usage.
    rate_limit.rate_limit_auth(request_b)


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_login_endpoint_rate_limited(client):
    for _ in range(rate_limit._MAX_REQUESTS):
        client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "wrong"})

    resp = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "wrong"})
    assert resp.status_code == 429


@pytest.fixture()
def campaign_with_daily_limit(db_session):
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

    campaign = Campaign(organisation_id=org.id, name="Capped campaign", integration_id=integration.id, max_daily_sends=1)
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


@pytest.fixture(autouse=True)
def mocked_gmail(monkeypatch):
    monkeypatch.setattr(email_sender, "get_valid_credentials", lambda db, integration: MagicMock())
    monkeypatch.setattr(
        email_sender.gmail_service, "send_email", lambda *a, **k: {"id": "msg-1", "threadId": "thread-1"}
    )


def test_send_blocked_once_daily_cap_reached(db_session, campaign_with_daily_limit):
    campaign, lead = campaign_with_daily_limit

    first_item = EmailQueueItem(
        campaign_id=campaign.id, lead_id=lead.id, subject="First", body="x", status=EmailQueueStatus.APPROVED
    )
    db_session.add(first_item)
    db_session.commit()
    email_sender.send_queued_email(db_session, first_item)

    second_item = EmailQueueItem(
        campaign_id=campaign.id, lead_id=lead.id, subject="Second", body="x", status=EmailQueueStatus.APPROVED
    )
    db_session.add(second_item)
    db_session.commit()

    with pytest.raises(email_sender.EmailSendError, match="daily limit"):
        email_sender.send_queued_email(db_session, second_item)
