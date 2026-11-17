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


def test_register_login_and_create_lead(client):
    register_resp = client.post(
        "/api/auth/register",
        json={
            "organisation_name": "Haki Systems",
            "full_name": "Admin User",
            "email": "admin@hakisystems.co.zw",
            "password": "a-strong-password",
        },
    )
    assert register_resp.status_code == 200
    token = register_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me_resp = client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["role"] == "admin"

    profile_resp = client.get("/api/company-profile", headers=headers)
    assert profile_resp.status_code == 200
    assert profile_resp.json()["company_name"] == "Haki Systems"

    lead_resp = client.post(
        "/api/leads",
        headers=headers,
        json={
            "business_name": "Example Hotel",
            "website": "https://example-hotel.co.zw",
            "country": "Zimbabwe",
            "city": "Harare",
            "industry": "Hospitality",
        },
    )
    assert lead_resp.status_code == 201
    assert lead_resp.json()["status"] == "new"

    list_resp = client.get("/api/leads", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1


def test_duplicate_registration_rejected(client):
    payload = {
        "organisation_name": "Haki Systems",
        "full_name": "Admin User",
        "email": "duplicate@hakisystems.co.zw",
        "password": "a-strong-password",
    }
    first = client.post("/api/auth/register", json=payload)
    assert first.status_code == 200

    second = client.post("/api/auth/register", json=payload)
    assert second.status_code == 400


def test_login_with_wrong_password_rejected(client):
    client.post(
        "/api/auth/register",
        json={
            "organisation_name": "Haki Systems",
            "full_name": "Admin User",
            "email": "login-test@hakisystems.co.zw",
            "password": "a-strong-password",
        },
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": "login-test@hakisystems.co.zw", "password": "wrong-password"},
    )
    assert resp.status_code == 401
