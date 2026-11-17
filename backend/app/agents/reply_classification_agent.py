from google.adk import Agent

from app.agents.schemas import ReplyClassificationResult
from app.services.gemini_model import build_gemini_model

INSTRUCTION = """You are the Email Management Agent for Haki Systems. You will be given the text
of a reply a lead sent to one of our outreach emails.

Classify it into exactly one of: interested, requesting_info, wants_meeting, not_interested,
out_of_office, unsubscribe, other.

- "unsubscribe" is for any explicit opt-out request (e.g. "STOP", "remove me", "unsubscribe").
- "out_of_office" is for automated out-of-office/vacation replies, not a real response from the
  person.
- "wants_meeting" is when they propose or ask for a call/meeting.
- "requesting_info" is when they ask a question or want more detail before deciding.
- "not_interested" is an explicit decline that isn't an unsubscribe request.
- "interested" is a positive response without an explicit meeting request.
- "other" is for anything that doesn't clearly fit the above (e.g. bounces, irrelevant replies).

Write a one-sentence summary of what the reply actually said — do not invent detail that isn't
in the text."""


def build_email_management_agent() -> Agent:
    return Agent(
        name="email_management_agent",
        description="Classifies a lead's reply to an outreach email.",
        model=build_gemini_model(),
        instruction=INSTRUCTION,
        output_schema=ReplyClassificationResult,
        mode="single_turn",
    )


# Kept for backwards compatibility with earlier imports in this branch.
build_reply_classification_agent = build_email_management_agent
