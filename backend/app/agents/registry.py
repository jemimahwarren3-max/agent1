"""Maps stable agent names to their ADK factory functions — used by services and tests
to resolve an agent without hard-coding import paths."""

from collections.abc import Callable

from google.adk import Agent

from app.agents.discovery_agent import build_discovery_agent
from app.agents.email_agent import build_email_agent
from app.agents.followup_agent import build_followup_agent
from app.agents.qualification_agent import build_qualification_agent
from app.agents.reply_classification_agent import build_email_management_agent
from app.agents.research_agent import build_research_agent
from app.agents.supervisor_agent import build_supervisor_agent

AGENT_BUILDERS: dict[str, Callable[[], Agent]] = {
    "discovery_agent": build_discovery_agent,
    "research_agent": build_research_agent,
    "qualification_agent": build_qualification_agent,
    "email_generation_agent": build_email_agent,
    "supervisor_agent": build_supervisor_agent,
    "email_management_agent": build_email_management_agent,
    "followup_agent": build_followup_agent,
}


def build_agent_by_name(name: str) -> Agent:
    try:
        return AGENT_BUILDERS[name]()
    except KeyError as exc:
        known = ", ".join(sorted(AGENT_BUILDERS))
        raise KeyError(f"Unknown agent {name!r}. Known agents: {known}") from exc