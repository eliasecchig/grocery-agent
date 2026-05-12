"""Integration tests for the grocery agent.

Tests that the agent loads, responds to messages, and calls
the right tools. Uses InMemorySessionService — no external
services needed except Vertex AI for the LLM.
"""

from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent import root_agent


def _run_agent(prompt: str) -> list:
    session_service = InMemorySessionService()
    session = session_service.create_session_sync(user_id="test_user", app_name="test")
    runner = Runner(agent=root_agent, session_service=session_service, app_name="test")

    message = types.Content(
        role="user", parts=[types.Part.from_text(text=prompt)]
    )

    return list(
        runner.run(
            new_message=message,
            user_id="test_user",
            session_id=session.id,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        )
    )


def test_agent_responds():
    """Agent returns at least one event with text content."""
    events = _run_agent("Ciao, cosa puoi fare?")
    assert len(events) > 0

    has_text = any(
        event.content
        and event.content.parts
        and any(part.text for part in event.content.parts)
        for event in events
    )
    assert has_text


def test_search_tool_called():
    """Agent calls store_graphql for product search queries."""
    events = _run_agent("Search for pasta barilla")
    tool_calls = [
        part.function_call.name
        for event in events
        if event.content and event.content.parts
        for part in event.content.parts
        if part.function_call
    ]
    assert "store_graphql" in tool_calls
