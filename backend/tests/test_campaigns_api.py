import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.models.leads import Lead


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def admin_headers_and_org(client, db_session):
    resp = client.post(
        "/api/auth/register",
        json={
            "organisation_name": "Haki Systems",
            "full_name": "Admin User",
            "email": "campaigns-admin@hakisystems.co.zw",
            "password": "a-strong-password",
        },
    )
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    me = client.get("/api/auth/me", headers=headers).json()
    return headers, me["organisation_id"]


def test_create_update_campaign(client, admin_headers_and_org):
    headers, _ = admin_headers_and_org
    create_resp = client.post(
        "/api/campaigns",
        headers=headers,
        json={"name": "Hospitality push", "target_country": "Zimbabwe", "max_daily_sends": 10},
    )
    assert create_resp.status_code == 201
    campaign = create_resp.json()
    assert campaign["max_daily_sends"] == 10
    assert campaign["approval_mode"] == "manual"

    update_resp = client.patch(
        f"/api/campaigns/{campaign['id']}", headers=headers, json={"max_daily_sends": 5}
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["max_daily_sends"] == 5


def test_create_campaign_rejects_invalid_approval_mode(client, admin_headers_and_org):
    headers, _ = admin_headers_and_org
    resp = client.post(
        "/api/campaigns", headers=headers, json={"name": "x", "approval_mode": "whenever"}
    )
    assert resp.status_code == 400


def test_match_leads_adds_matching_leads_and_skips_suppressed(client, admin_headers_and_org, db_session):
    headers, org_id = admin_headers_and_org

    db_session.add(
        Lead(
            organisation_id=org_id,
            business_name="Matching Hotel",
            website="https://matching-hotel.co.zw",
            country="Zimbabwe",
            business_email="owner@matching-hotel.co.zw",
        )
    )
    db_session.add(
        Lead(
            organisation_id=org_id,
            business_name="Other Country Hotel",
            website="https://other-country.co.zw",
            country="Zambia",
        )
    )
    db_session.add(
        Lead(
            organisation_id=org_id,
            business_name="Unsubscribed Hotel",
            website="https://unsub-hotel.co.zw",
            country="Zimbabwe",
            is_unsubscribed=True,
        )
    )
    db_session.commit()

    campaign_resp = client.post(
        "/api/campaigns", headers=headers, json={"name": "Zim push", "target_country": "Zimbabwe"}
    )
    campaign_id = campaign_resp.json()["id"]

    match_resp = client.post(f"/api/campaigns/{campaign_id}/match-leads", headers=headers)
    assert match_resp.status_code == 200
    body = match_resp.json()
    assert body["matched_count"] == 1
    assert body["skipped_suppressed_count"] == 1

    leads_resp = client.get(f"/api/campaigns/{campaign_id}/leads", headers=headers)
    assert [lead["business_name"] for lead in leads_resp.json()] == ["Matching Hotel"]

    # Running it again doesn't double-add the already-matched lead.
    second_match = client.post(f"/api/campaigns/{campaign_id}/match-leads", headers=headers)
    assert second_match.json()["matched_count"] == 0
