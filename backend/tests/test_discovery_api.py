"""API-level tests for the discovery job state machine. The background task is
replaced with a no-op so the endpoints are tested in isolation from the (Gemini-
dependent) orchestrator."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.session import get_db
from app.main import app


@pytest.fixture()
def client(db_session, monkeypatch):
    # Neutralize the real background task — we're testing the HTTP state machine here.
    import app.api.discovery as discovery_api

    monkeypatch.setattr(discovery_api, "run_discovery_job_sync", lambda job_id: None)

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
            "full_name": "Admin",
            "email": "admin@hakisystems.co.zw",
            "password": "a-strong-password",
        },
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_start_creates_pending_job(client, auth_headers):
    resp = client.post(
        "/api/discovery/start",
        headers=auth_headers,
        json={"country": "Zimbabwe", "city": "Harare", "industry": "hospitality", "num_leads": 10},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "pending"
    assert body["search_params"]["city"] == "Harare"
    assert "campaign_id" not in body["search_params"]


def test_pause_resume_cancel_state_machine(client, auth_headers):
    job_id = client.post(
        "/api/discovery/start", headers=auth_headers, json={"industry": "hospitality"}
    ).json()["id"]

    # pending -> paused
    assert client.post(f"/api/discovery/jobs/{job_id}/pause", headers=auth_headers).json()["status"] == "paused"
    # paused -> running (resume)
    assert client.post(f"/api/discovery/jobs/{job_id}/resume", headers=auth_headers).json()["status"] == "running"
    # running -> cancelled
    assert client.post(f"/api/discovery/jobs/{job_id}/cancel", headers=auth_headers).json()["status"] == "cancelled"
    # cancelled is terminal -> cannot pause
    assert client.post(f"/api/discovery/jobs/{job_id}/pause", headers=auth_headers).status_code == 400


def test_cannot_resume_a_running_job(client, auth_headers):
    job_id = client.post("/api/discovery/start", headers=auth_headers, json={"industry": "x"}).json()["id"]
    client.post(f"/api/discovery/jobs/{job_id}/pause", headers=auth_headers)
    client.post(f"/api/discovery/jobs/{job_id}/resume", headers=auth_headers)
    # now running; resume again should 400
    assert client.post(f"/api/discovery/jobs/{job_id}/resume", headers=auth_headers).status_code == 400


def test_list_and_get_jobs(client, auth_headers):
    client.post("/api/discovery/start", headers=auth_headers, json={"industry": "hospitality"})
    jobs = client.get("/api/discovery/jobs", headers=auth_headers).json()
    assert len(jobs) == 1
    one = client.get(f"/api/discovery/jobs/{jobs[0]['id']}", headers=auth_headers)
    assert one.status_code == 200


def test_other_org_cannot_see_job(client, auth_headers):
    job_id = client.post("/api/discovery/start", headers=auth_headers, json={"industry": "x"}).json()["id"]

    other = client.post(
        "/api/auth/register",
        json={
            "organisation_name": "Other Co",
            "full_name": "Other",
            "email": "other@example.com",
            "password": "a-strong-password",
        },
    ).json()["access_token"]
    resp = client.get(f"/api/discovery/jobs/{job_id}", headers={"Authorization": f"Bearer {other}"})
    assert resp.status_code == 404
