import httpx
import pytest

from app.core.config import settings
from app.services.search_provider import (
    GoogleCustomSearchProvider,
    SearchProviderError,
    get_search_provider,
)


@pytest.mark.asyncio
async def test_search_raises_when_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CSE_API_KEY", "")
    monkeypatch.setattr(settings, "GOOGLE_CSE_ENGINE_ID", "")
    provider = GoogleCustomSearchProvider()
    with pytest.raises(SearchProviderError, match="not configured"):
        await provider.search("hotels in Harare")


@pytest.mark.asyncio
async def test_search_parses_results(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CSE_API_KEY", "fake-key")
    monkeypatch.setattr(settings, "GOOGLE_CSE_ENGINE_ID", "fake-engine")

    async def fake_get(self, url, params=None, **kwargs):
        return httpx.Response(
            200,
            json={
                "items": [
                    {"title": "Example Hotel", "link": "https://example-hotel.co.zw", "snippet": "A hotel."}
                ]
            },
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    provider = GoogleCustomSearchProvider()
    results = await provider.search("hotels in Harare")
    assert results == [
        {"title": "Example Hotel", "link": "https://example-hotel.co.zw", "snippet": "A hotel."}
    ]


@pytest.mark.asyncio
async def test_search_raises_on_non_200(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CSE_API_KEY", "fake-key")
    monkeypatch.setattr(settings, "GOOGLE_CSE_ENGINE_ID", "fake-engine")

    async def fake_get(self, url, params=None, **kwargs):
        return httpx.Response(403, text="quota exceeded", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    provider = GoogleCustomSearchProvider()
    with pytest.raises(SearchProviderError, match="403"):
        await provider.search("hotels in Harare")


def test_get_search_provider_unknown_raises(monkeypatch):
    monkeypatch.setattr(settings, "SEARCH_PROVIDER", "bing")
    with pytest.raises(SearchProviderError):
        get_search_provider()
