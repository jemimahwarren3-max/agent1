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
def auth_headers(client):
    resp = client.post(
        "/api/auth/register",
        json={
            "organisation_name": "Haki Systems",
            "full_name": "Admin User",
            "email": "templates-test@hakisystems.co.zw",
            "password": "a-strong-password",
        },
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_list_update_delete_template(client, auth_headers):
    create_resp = client.post(
        "/api/templates",
        headers=auth_headers,
        json={
            "name": "Website intro",
            "category": "website_development",
            "subject": "A quick idea for {{business_name}}",
            "body": "Hello,\n\nWe help businesses like yours...",
        },
    )
    assert create_resp.status_code == 201
    template = create_resp.json()
    assert template["is_approved"] is False

    list_resp = client.get("/api/templates", headers=auth_headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    update_resp = client.put(
        f"/api/templates/{template['id']}",
        headers=auth_headers,
        json={"is_approved": True},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["is_approved"] is True
    assert update_resp.json()["name"] == "Website intro"

    delete_resp = client.delete(f"/api/templates/{template['id']}", headers=auth_headers)
    assert delete_resp.status_code == 204

    list_resp = client.get("/api/templates", headers=auth_headers)
    assert list_resp.json() == []


def test_create_template_rejects_invalid_category(client, auth_headers):
    resp = client.post(
        "/api/templates",
        headers=auth_headers,
        json={"name": "Bad", "category": "not_a_real_category", "subject": "x", "body": "x"},
    )
    assert resp.status_code == 400


def test_cannot_access_another_organisations_template(client, auth_headers):
    create_resp = client.post(
        "/api/templates",
        headers=auth_headers,
        json={
            "name": "Org A template",
            "category": "general_introduction",
            "subject": "Hi",
            "body": "Hello",
        },
    )
    template_id = create_resp.json()["id"]

    other_org_resp = client.post(
        "/api/auth/register",
        json={
            "organisation_name": "Other Org",
            "full_name": "Other Admin",
            "email": "other-org@example.com",
            "password": "a-strong-password",
        },
    )
    other_headers = {"Authorization": f"Bearer {other_org_resp.json()['access_token']}"}

    resp = client.get(f"/api/templates/{template_id}", headers=other_headers)
    assert resp.status_code == 404
