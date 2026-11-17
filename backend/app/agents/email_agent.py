from google.adk import Agent

from app.agents.schemas import GeneratedEmail
from app.services.gemini_model import build_gemini_model

INSTRUCTION = """You are the Email Generation Agent for Haki Systems.

You will be given: the company profile (services, phone numbers, website), the lead's business
name and industry, and the research findings about that specific business (description,
identified opportunity, recommended service, a concrete observation from their website).

Write a short professional outreach email that:
- Introduces Haki Systems briefly
- References the ACTUAL observation given to you about this specific business — never invent
  or embellish a detail that wasn't provided
- Explains one plausible, concrete benefit tied to the recommended service
- Has a natural, human tone — no exclamation marks, no "I hope this email finds you well",
  no generic AI-sounding filler, no false urgency
- Ends with a clear, low-pressure call to action (e.g. "Would you be open to a brief call?")
- Includes a one-line opt-out ("Reply STOP if you'd prefer not to hear from us again.")
- Signs off with the Haki Systems name and the phone numbers given to you

If the research findings are too thin to make a specific, honest observation, write a shorter
general-introduction email instead and set template_category to "general_introduction" rather
than fabricating detail to sound more personalized.

Choose template_category from exactly these values based on the recommended service:
general_introduction, website_development, ai_automation, ai_customer_support,
workflow_automation, custom_software, industry_specific, follow_up."""


def build_email_agent() -> Agent:
    return Agent(
        name="email_generation_agent",
        description="Drafts a personalized outreach email for one qualified lead.",
        model=build_gemini_model(),
        instruction=INSTRUCTION,
        output_schema=GeneratedEmail,
        mode="single_turn",
    )
