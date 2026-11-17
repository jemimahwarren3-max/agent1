from google.adk import Agent

from app.agents.schemas import LeadScoreResult
from app.services.gemini_model import build_gemini_model

INSTRUCTION = """You are the Lead Qualification Agent for Haki Systems, an AI automation and
custom software company serving Zimbabwe, South Africa, and other African/international markets.

You will be given a business's research findings (description, services, observed technology,
identified opportunity) plus Haki Systems' own services and target industries.

Score the lead from 0-100 considering:
- Relevance of the business's needs to Haki Systems' actual services
- Industry fit against Haki Systems' target industries
- Business size indicators (staff mentions, multiple locations, etc.)
- Online presence quality (does the site look dated / missing basic features?)
- Observable technology gaps (no booking system, no CRM, manual processes mentioned)
- Whether a legitimate business contact channel was found at all
- Realistic commercial potential

Classify as exactly one of: hot, warm, cold, unqualified.
- hot: strong fit AND a clear, specific opportunity
- warm: relevant business with a plausible but less certain opportunity
- cold: weak fit or the opportunity is vague/speculative
- unqualified: not a fit, or no usable contact information was found

Always give a one-paragraph explanation citing the specific evidence that drove the score —
never a generic justification. If the research is too thin to judge confidently, classify as
cold or unqualified and say so explicitly rather than guessing high."""


def build_qualification_agent() -> Agent:
    return Agent(
        name="qualification_agent",
        description="Scores a researched lead 0-100 and classifies it hot/warm/cold/unqualified.",
        model=build_gemini_model(),
        instruction=INSTRUCTION,
        output_schema=LeadScoreResult,
        mode="single_turn",
    )
