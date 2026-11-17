import base64
from unittest.mock import MagicMock

from app.services import gmail_service


def test_send_email_builds_correct_request(monkeypatch):
    fake_messages = MagicMock()
    fake_messages.send.return_value.execute.return_value = {"id": "msg-1", "threadId": "thread-1"}
    fake_client = MagicMock()
    fake_client.users.return_value.messages.return_value = fake_messages
    monkeypatch.setattr(gmail_service, "_gmail_client", lambda credentials: fake_client)

    result = gmail_service.send_email(MagicMock(), "lead@example.com", "Subject line", "Body text")

    assert result == {"id": "msg-1", "threadId": "thread-1"}
    _, kwargs = fake_messages.send.call_args
    assert kwargs["userId"] == "me"
    raw_bytes = base64.urlsafe_b64decode(kwargs["body"]["raw"])
    assert b"lead@example.com" in raw_bytes
    assert b"Subject line" in raw_bytes
    assert b"Body text" in raw_bytes


def test_extract_message_text_from_plain_part():
    encoded = base64.urlsafe_b64encode(b"Hello there").decode()
    message = {"payload": {"parts": [{"mimeType": "text/plain", "body": {"data": encoded}}]}}
    assert gmail_service.extract_message_text(message) == "Hello there"


def test_extract_message_text_from_top_level_body():
    encoded = base64.urlsafe_b64encode(b"Top level body").decode()
    message = {"payload": {"body": {"data": encoded}}}
    assert gmail_service.extract_message_text(message) == "Top level body"


def test_extract_message_text_returns_empty_when_no_data():
    assert gmail_service.extract_message_text({"payload": {}}) == ""


def test_is_from_us():
    message = {"payload": {"headers": [{"name": "From", "value": "Haki Systems <sales@hakisystems.co.zw>"}]}}
    assert gmail_service.is_from_us(message, "sales@hakisystems.co.zw")
    assert not gmail_service.is_from_us(message, "someoneelse@example.com")
