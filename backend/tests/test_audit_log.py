import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app


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
def admin_headers(client):
    resp = client.post(
        "/api/auth/register",
        json={
            "organisation_name": "Haki Systems",
            "full_name": "Admin User",
            "email": "audit-admin@hakisystems.co.zw",
            "password": "a-strong-password",
        },
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_creating_a_template_is_audited(client, admin_headers):
    client.post(
        "/api/templates",
        headers=admin_headers,
        json={"name": "x", "category": "general_introduction", "subject": "x", "body": "x"},
    )
    resp = client.get("/api/audit-logs", headers=admin_headers)
    assert resp.status_code == 200
    actions = [(log["action"], log["entity_type"]) for log in resp.json()]
    assert ("create", "email_template") in actions


def test_creating_a_campaign_is_audited(client, admin_headers):
    client.post("/api/campaigns", headers=admin_headers, json={"name": "Test campaign"})
    resp = client.get("/api/audit-logs", headers=admin_headers)
    actions = [(log["action"], log["entity_type"]) for log in resp.json()]
    assert ("create", "campaign") in actions


def test_inviting_a_user_is_audited(client, admin_headers):
    client.post(
        "/api/auth/users",
        headers=admin_headers,
        json={
            "email": "audit-invitee@hakisystems.co.zw",
            "full_name": "x",
            "password": "a-strong-password",
            "role": "member",
        },
    )
    resp = client.get("/api/audit-logs", headers=admin_headers)
    actions = [(log["action"], log["entity_type"]) for log in resp.json()]
    assert ("invite", "user") in actions


def test_audit_logs_are_scoped_to_organisation(client):
    org_a = client.post(
        "/api/auth/register",
        json={
            "organisation_name": "Org A",
            "full_name": "Admin A",
            "email": "org-a-admin@example.com",
            "password": "a-strong-password",
        },
    )
    org_a_headers = {"Authorization": f"Bearer {org_a.json()['access_token']}"}
    client.post(
        "/api/templates",
        headers=org_a_headers,
        json={"name": "x", "category": "general_introduction", "subject": "x", "body": "x"},
    )

    org_b = client.post(
        "/api/auth/register",
        json={
            "organisation_name": "Org B",
            "full_name": "Admin B",
            "email": "org-b-admin@example.com",
            "password": "a-strong-password",
        },
    )
    org_b_headers = {"Authorization": f"Bearer {org_b.json()['access_token']}"}

    resp = client.get("/api/audit-logs", headers=org_b_headers)
    assert resp.json() == []
