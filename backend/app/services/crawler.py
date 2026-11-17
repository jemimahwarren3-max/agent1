"""Crawl4AI wrapper. Crawl4AI crawls a given URL — it is not itself a search
engine, so this is only ever handed URLs that the Discovery Agent already found
(or a contact page the Research Agent asks for by following a link)."""

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig


class CrawlError(RuntimeError):
    pass


async def crawl_page(url: str, max_markdown_chars: int = 15000) -> dict:
    """Fetches one URL and returns its cleaned content.

    Returns a dict: {url, success, markdown, links, error}. `links` is the list
    of same-site internal link URLs discovered on the page, so a caller can
    decide to follow one (e.g. a "Contact Us" link) in a second call.
    """
    browser_config = BrowserConfig(headless=True)
    run_config = CrawlerRunConfig(
        check_robots_txt=True,
        page_timeout=30000,
        word_count_threshold=20,
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url=url, config=run_config)

    if not result.success:
        return {
            "url": url,
            "success": False,
            "markdown": "",
            "links": [],
            "error": result.error_message or "Unknown crawl failure",
        }

    internal_links = [link.get("href", "") for link in (result.links.get("internal", []) or [])]

    markdown_text = (result.markdown.raw_markdown if hasattr(result.markdown, "raw_markdown") else str(result.markdown)) or ""

    return {
        "url": url,
        "success": True,
        "markdown": markdown_text[:max_markdown_chars],
        "links": internal_links[:30],
        "error": "",
    }
