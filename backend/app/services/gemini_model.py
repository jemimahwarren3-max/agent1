"""Builds a Gemini model instance for ADK agents, pointed at the configured
API key rather than relying on ambient GOOGLE_API_KEY/GEMINI_API_KEY env vars.
"""

from google.adk.models import Gemini

from app.core.config import settings

DEFAULT_MODEL_NAME = "gemini-2.5-flash"


class GeminiNotConfiguredError(RuntimeError):
    pass


def build_gemini_model(model_name: str = DEFAULT_MODEL_NAME) -> Gemini:
    if not settings.GEMINI_API_KEY:
        raise GeminiNotConfiguredError(
            "GEMINI_API_KEY is not set. Get one at https://aistudio.google.com/app/apikey "
            "and put it in .env — see docs/GOOGLE_CLOUD_SETUP.md."
        )
    return Gemini(model=model_name, client_kwargs={"api_key": settings.GEMINI_API_KEY})
