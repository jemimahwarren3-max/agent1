"""Thin wrapper around the Gmail API — send, and read a thread's messages for
reply monitoring. Takes already-refreshed `Credentials`; callers are
responsible for persisting any refreshed token (see app.api.integrations)."""

import base64
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def _gmail_client(credentials: Credentials):
    return build("gmail", "v1", credentials=credentials, cache_discovery=False)


def get_profile_email(credentials: Credentials) -> str:
    profile = _gmail_client(credentials).users().getProfile(userId="me").execute()
    return profile["emailAddress"]


def send_email(credentials: Credentials, to: str, subject: str, body: str) -> dict:
    """Sends a plain-text email. Returns the Gmail API message resource, which
    includes `id` (message id) and `threadId`."""
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return (
        _gmail_client(credentials)
        .users()
        .messages()
        .send(userId="me", body={"raw": raw})
        .execute()
    )


def list_thread_messages(credentials: Credentials, thread_id: str) -> list[dict]:
    """Returns the full message resources (format=full) in a thread, oldest first."""
    thread = _gmail_client(credentials).users().threads().get(userId="me", id=thread_id, format="full").execute()
    return thread.get("messages", [])


def extract_message_text(message: dict) -> str:
    """Pulls the plain-text body out of a Gmail message resource."""
    payload = message.get("payload", {})
    parts = payload.get("parts") or [payload]
    for part in parts:
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode(errors="replace")
    body = payload.get("body", {})
    if body.get("data"):
        return base64.urlsafe_b64decode(body["data"]).decode(errors="replace")
    return ""


def is_from_us(message: dict, our_email: str) -> bool:
    headers = {h["name"].lower(): h["value"] for h in message.get("payload", {}).get("headers", [])}
    return our_email.lower() in headers.get("from", "").lower()
