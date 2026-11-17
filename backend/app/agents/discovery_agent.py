from google.adk import Agent
from google.adk.tools import FunctionTool

from app.agents.schemas import DiscoveryResult
from app.services.gemini_model import build_gemini_model
from app.services.search_provider import get_search_provider

INSTRUCTION = """You are the Lead Discovery Agent for Haki Systems.

You are given a target country/city, industry, business type, and keywords describing the kind
of opportunity Haki Systems wants to pursue (e.g. "hotels that could benefit from booking
automation"). Use the `web_search` tool with well-formed search queries to find real businesses
matching that description — vary your queries (by city, by business-type synonym, by keyword)
rather than reusing one query repeatedly, since a single query rarely returns enough distinct
results.

For each business you find:
- Only include it if the search result clearly points to that business's own official website —
  never a directory listing, aggregator, review site, or social media profile page.
- Extract the business name as it appears, not as you infer or guess it.
- Record which search result (source URL) led you to it.
- Do not fabricate a business that wasn't in your search results.
- Skip anything you cannot confirm has a real, working business website.

Stop once you've gathered as many qualifying businesses as reasonably findable from a handful of
searches, deduplicating by website domain. If a search turns up nothing useful, try a different
phrasing rather than giving up after one query."""


async def web_search(query: str, num_results: int = 10) -> dict:
    """Search the web for businesses matching a query.

    Args:
        query: The search query, e.g. "hotels in Harare Zimbabwe".
        num_results: How many results to return (max 10 per call).

    Returns:
        A dict with a "results" key: a list of {title, link, snippet} objects.
    """
    provider = get_search_provider()
    results = await provider.search(query, num_results=num_results)
    return {"results": results}


def build_discovery_agent() -> Agent:
    return Agent(
        name="discovery_agent",
        description="Searches the web for businesses matching a target market/industry/keyword set.",
        model=build_gemini_model(),
        instruction=INSTRUCTION,
        tools=[FunctionTool(web_search)],
        output_schema=DiscoveryResult,
        mode="single_turn",
    )
