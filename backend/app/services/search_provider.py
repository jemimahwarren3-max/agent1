"""Search API abstraction so the underlying provider can be swapped without
touching the Discovery Agent. Only Google Programmable Search Engine (Custom
Search JSON API) is implemented — the brief calls this out as the default
assumption, with Bing/SerpAPI as viable swaps behind this same interface.
"""

from abc import ABC, abstractmethod

import httpx

from app.core.config import settings


class SearchResult(dict):
    """title, link, snippet — kept as a plain dict so it's trivially JSON-serializable
    for the ADK tool response."""


class SearchProviderError(RuntimeError):
    pass


class SearchProvider(ABC):
    @abstractmethod
    async def search(self, query: str, num_results: int = 10) -> list[dict]:
        ...


class GoogleCustomSearchProvider(SearchProvider):
    ENDPOINT = "https://www.googleapis.com/customsearch/v1"

    async def search(self, query: str, num_results: int = 10) -> list[dict]:
        if not settings.GOOGLE_CSE_API_KEY or not settings.GOOGLE_CSE_ENGINE_ID:
            raise SearchProviderError(
                "GOOGLE_CSE_API_KEY / GOOGLE_CSE_ENGINE_ID are not configured. "
                "See docs/GOOGLE_CLOUD_SETUP.md to provision a Programmable Search Engine."
            )

        num_results = min(num_results, 10)  # CSE caps at 10 per request
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                self.ENDPOINT,
                params={
                    "key": settings.GOOGLE_CSE_API_KEY,
                    "cx": settings.GOOGLE_CSE_ENGINE_ID,
                    "q": query,
                    "num": num_results,
                },
            )
        if resp.status_code != 200:
            raise SearchProviderError(f"Search API returned {resp.status_code}: {resp.text[:500]}")

        data = resp.json()
        return [
            {
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
            }
            for item in data.get("items", [])
        ]


def get_search_provider() -> SearchProvider:
    if settings.SEARCH_PROVIDER == "google_cse":
        return GoogleCustomSearchProvider()
    raise SearchProviderError(f"Unknown SEARCH_PROVIDER: {settings.SEARCH_PROVIDER}")
