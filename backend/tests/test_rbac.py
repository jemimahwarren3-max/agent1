"""Confirms role-gated endpoints actually reject a member, not just that an
admin can use them (every existing test registers the first/admin user, so
without this nothing would catch a missing Depends(require_role(...)))."""

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
def admin_and_member_headers(client):
    admin_resp = client.post(
        "/api/auth/register",
        json={
            "organisation_name": "Haki Systems",
            "full_name": "Admin User",
            "email": "rbac-admin@hakisystems.co.zw",
            "password": "a-strong-password",
        },
    )
    admin_headers = {"Authorization": f"Bearer {admin_resp.json()['access_token']}"}

    invite_resp = client.post(
        "/api/auth/users",
        headers=admin_headers,
        json={
            "email": "rbac-member@hakisystems.co.zw",
            "full_name": "Member User",
            "password": "a-strong-password",
            "role": "member",
        },
    )
    assert invite_resp.status_code == 201

    login_resp = client.post(
        "/api/auth/login", json={"email": "rbac-member@hakisystems.co.zw", "password": "a-strong-password"}
    )
    member_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}
    return admin_headers, member_headers


def test_member_cannot_create_template(client, admin_and_member_headers):
    _, member_headers = admin_and_member_headers
    resp = client.post(
        "/api/templates",
        headers=member_headers,
        json={"name": "x", "category": "general_introduction", "subject": "x", "body": "x"},
    )
    assert resp.status_code == 403


def test_admin_can_create_template(client, admin_and_member_headers):
    admin_headers, _ = admin_and_member_headers
    resp = client.post(
        "/api/templates",
        headers=admin_headers,
        json={"name": "x", "category": "general_introduction", "subject": "x", "body": "x"},
    )
    assert resp.status_code == 201


def test_member_cannot_create_campaign(client, admin_and_member_headers):
    _, member_headers = admin_and_member_headers
    resp = client.post("/api/campaigns", headers=member_headers, json={"name": "Test campaign"})
    assert resp.status_code == 403


def test_member_cannot_connect_google_integration(client, admin_and_member_headers):
    _, member_headers = admin_and_member_headers
    resp = client.get("/api/integrations/google/authorize", headers=member_headers)
    assert resp.status_code == 403


def test_member_cannot_invite_users(client, admin_and_member_headers):
    _, member_headers = admin_and_member_headers
    resp = client.post(
        "/api/auth/users",
        headers=member_headers,
        json={"email": "nope@example.com", "full_name": "x", "password": "a-strong-password", "role": "member"},
    )
    assert resp.status_code == 403


def test_member_cannot_view_audit_log(client, admin_and_member_headers):
    _, member_headers = admin_and_member_headers
    resp = client.get("/api/audit-logs", headers=member_headers)
    assert resp.status_code == 403


def test_member_can_still_list_leads(client, admin_and_member_headers):
    _, member_headers = admin_and_member_headers
    resp = client.get("/api/leads", headers=member_headers)
    assert resp.status_code == 200


def test_invite_rejects_duplicate_email(client, admin_and_member_headers):
    admin_headers, _ = admin_and_member_headers
    resp = client.post(
        "/api/auth/users",
        headers=admin_headers,
        json={
            "email": "rbac-member@hakisystems.co.zw",
            "full_name": "Dup",
            "password": "a-strong-password",
            "role": "member",
        },
    )
    assert resp.status_code == 400


def test_invite_rejects_invalid_role(client, admin_and_member_headers):
    admin_headers, _ = admin_and_member_headers
    resp = client.post(
        "/api/auth/users",
        headers=admin_headers,
        json={
            "email": "rbac-newperson@hakisystems.co.zw",
            "full_name": "x",
            "password": "a-strong-password",
            "role": "superuser",
        },
    )
    assert resp.status_code == 400
