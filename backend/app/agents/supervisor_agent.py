from google.adk import Agent

from app.agents.discovery_agent import build_discovery_agent
from app.agents.email_agent import build_email_agent
from app.agents.qualification_agent import build_qualification_agent
from app.agents.research_agent import build_research_agent
from app.services.gemini_model import build_gemini_model

INSTRUCTION = """You are the Supervisor Agent coordinating Haki Systems' prospecting pipeline.

You have four specialist agents available as tools: discovery_agent, research_agent,
qualification_agent, and email_generation_agent. Given a campaign brief (target country/city,
industry, keywords, and how many leads to pursue), run the pipeline in this order for each
business:

1. Call discovery_agent to find candidate businesses matching the brief.
2. For each candidate, call research_agent with its name and website to gather verifiable facts.
3. Call qualification_agent with the research findings to score and classify the lead.
4. Only for leads classified "hot" or "warm", call email_generation_agent to draft an outreach
   email using the research findings and the company profile you were given.

You never send anything — you only draft. Sending requires separate human approval outside your
control, and you have no tool capable of sending email.

If a specialist agent fails or returns something you can't use (e.g. research_agent reports
could_not_extract_reason), skip that business, note why, and continue with the rest rather than
stopping the whole run.

When finished, give a concise plain-text summary: how many businesses were found, how many were
researched successfully, the breakdown by classification (hot/warm/cold/unqualified), and how
many emails were drafted."""


def build_supervisor_agent() -> Agent:
    discovery = build_discovery_agent()
    research = build_research_agent()
    qualification = build_qualification_agent()
    email = build_email_agent()

    return Agent(
        name="supervisor_agent",
        description="Coordinates discovery, research, qualification, and email drafting for a campaign brief.",
        model=build_gemini_model(),
        instruction=INSTRUCTION,
        sub_agents=[discovery, research, qualification, email],
    )
