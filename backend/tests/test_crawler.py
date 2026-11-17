from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.services.crawler import crawl_page


class FakeMarkdown:
    def __init__(self, raw: str):
        self.raw_markdown = raw


def _fake_result(success=True, markdown="# Example\nSome content.", links=None, error=None):
    return SimpleNamespace(
        success=success,
        markdown=FakeMarkdown(markdown),
        links={"internal": links or []},
        error_message=error,
    )


@pytest.mark.asyncio
async def test_crawl_page_success():
    fake_result = _fake_result(links=[{"href": "https://example.com/contact"}])

    mock_crawler = AsyncMock()
    mock_crawler.arun.return_value = fake_result
    mock_crawler.__aenter__.return_value = mock_crawler
    mock_crawler.__aexit__.return_value = None

    with patch("app.services.crawler.AsyncWebCrawler", return_value=mock_crawler):
        result = await crawl_page("https://example.com")

    assert result["success"] is True
    assert "Example" in result["markdown"]
    assert result["links"] == ["https://example.com/contact"]


@pytest.mark.asyncio
async def test_crawl_page_failure():
    fake_result = _fake_result(success=False, error="403 Forbidden")

    mock_crawler = AsyncMock()
    mock_crawler.arun.return_value = fake_result
    mock_crawler.__aenter__.return_value = mock_crawler
    mock_crawler.__aexit__.return_value = None

    with patch("app.services.crawler.AsyncWebCrawler", return_value=mock_crawler):
        result = await crawl_page("https://example.com")

    assert result["success"] is False
    assert result["error"] == "403 Forbidden"
    assert result["markdown"] == ""


@pytest.mark.asyncio
async def test_crawl_page_truncates_markdown():
    fake_result = _fake_result(markdown="x" * 20000)

    mock_crawler = AsyncMock()
    mock_crawler.arun.return_value = fake_result
    mock_crawler.__aenter__.return_value = mock_crawler
    mock_crawler.__aexit__.return_value = None

    with patch("app.services.crawler.AsyncWebCrawler", return_value=mock_crawler):
        result = await crawl_page("https://example.com", max_markdown_chars=100)

    assert len(result["markdown"]) == 100
