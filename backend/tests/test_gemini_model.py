import pytest

from app.core.config import settings
from app.services.gemini_model import GeminiNotConfiguredError, build_gemini_model


def test_raises_when_no_api_key(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    with pytest.raises(GeminiNotConfiguredError):
        build_gemini_model()


def test_builds_model_when_key_present(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "fake-test-key")
    model = build_gemini_model()
    assert model.model == "gemini-2.5-flash"
