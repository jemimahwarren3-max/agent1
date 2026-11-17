"""Verifies every agent constructs correctly against the real ADK Agent class
(catches wrong field names / bad tool wiring) without making a live Gemini call."""

import pytest

from app.core.config import settings


@pytest.fixture(autouse=True)
def fake_gemini_key(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "fake-test-key")


def test_discovery_agent_builds_with_search_tool():
    from app.agents.discovery_agent import build_discovery_agent

    agent = build_discovery_agent()
    assert agent.name == "discovery_agent"
    assert agent.mode == "single_turn"
    assert len(agent.tools) == 1


def test_research_agent_builds_with_crawl_tool():
    from app.agents.research_agent import build_research_agent

    agent = build_research_agent()
    assert agent.name == "research_agent"
    assert len(agent.tools) == 1


def test_qualification_agent_builds():
    from app.agents.qualification_agent import build_qualification_agent

    agent = build_qualification_agent()
    assert agent.name == "qualification_agent"
    assert agent.output_schema is not None


def test_email_agent_builds():
    from app.agents.email_agent import build_email_agent

    agent = build_email_agent()
    assert agent.name == "email_generation_agent"


def test_supervisor_agent_wires_all_four_sub_agents():
    from app.agents.supervisor_agent import build_supervisor_agent

    supervisor = build_supervisor_agent()
    assert supervisor.name == "supervisor_agent"
    sub_names = {a.name for a in supervisor.sub_agents}
    assert sub_names == {
        "discovery_agent",
        "research_agent",
        "qualification_agent",
        "email_generation_agent",
    }
