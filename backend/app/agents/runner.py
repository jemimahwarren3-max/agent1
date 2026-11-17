"""Thin helper for invoking a single ADK agent and getting back its validated
structured output — used for the one-shot (qualify this lead / draft this email)
calls the rest of the backend makes, as opposed to a long multi-turn chat."""

import uuid

from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

APP_NAME = "haki-prospecting"


class AgentRunError(RuntimeError):
    pass


async def run_agent(agent: Agent, user_message: str, user_id: str = "system"):
    """Runs `agent` with a single user message and returns its structured output
    (an instance of the agent's `output_schema`, since every agent here sets one).
    """
    session_service = InMemorySessionService()
    session = await session_service.create_session(app_name=APP_NAME, user_id=user_id)
    runner = Runner(app_name=APP_NAME, agent=agent, session_service=session_service)

    content = types.Content(role="user", parts=[types.Part(text=user_message)])

    final_output = None
    last_text = None
    async for event in runner.run_async(
        user_id=user_id, session_id=session.id, new_message=content
    ):
        if event.output is not None:
            final_output = event.output
        if event.content and event.content.parts:
            texts = [p.text for p in event.content.parts if getattr(p, "text", None)]
            if texts:
                last_text = "\n".join(texts)

    if final_output is not None:
        return final_output

    raise AgentRunError(
        f"Agent '{agent.name}' did not return a structured output. "
        f"Last response text: {last_text!r}"
    )
