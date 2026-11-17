from google.adk import Agent

from app.agents.schemas import GeneratedEmail
from app.services.gemini_model import build_gemini_model

INSTRUCTION = """You are the Follow-up Agent for Haki Systems. The lead was sent an initial
outreach email and has not replied since. Write a brief, polite follow-up email that:

- References that this is a follow-up to the earlier email, without being pushy
- Restates the original value proposition in one sentence, using the same identified opportunity
  and recommended service you are given — never invent a new one
- Has a natural, human tone — no exclamation marks, no generic AI-sounding filler, no false
  urgency
- Ends with a clear, low-pressure call to action
- Includes a one-line opt-out ("Reply STOP if you'd prefer not to hear from us again.")
- Signs off with the Haki Systems name and the phone numbers given to you
- Is shorter than a typical first-touch email

Always set template_category to "follow_up"."""


def build_followup_agent() -> Agent:
    return Agent(
        name="followup_agent",
        description="Drafts a follow-up email for a lead who hasn't replied to the first outreach.",
        model=build_gemini_model(),
        instruction=INSTRUCTION,
        output_schema=GeneratedEmail,
        mode="single_turn",
    )
