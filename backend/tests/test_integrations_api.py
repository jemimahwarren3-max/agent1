import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
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
def auth_headers(client):
    resp = client.post(
        "/api/auth/register",
        json={
            "organisation_name": "Haki Systems",
            "full_name": "Admin User",
            "email": "integrations-test@hakisystems.co.zw",
            "password": "a-strong-password",
        },
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_authorize_returns_503_when_not_configured(client, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")
    resp = client.get("/api/integrations/google/authorize", headers=auth_headers)
    assert resp.status_code == 503


def test_authorize_returns_url_when_configured(client, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "fake-id")
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "fake-secret")
    resp = client.get("/api/integrations/google/authorize", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["authorize_url"].startswith("https://accounts.google.com/o/oauth2/auth")


def test_list_integrations_starts_empty(client, auth_headers):
    resp = client.get("/api/integrations", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_disconnect_nonexistent_integration_returns_404(client, auth_headers):
    resp = client.post(
        "/api/integrations/00000000-0000-0000-0000-000000000000/disconnect", headers=auth_headers
    )
    assert resp.status_code == 404
