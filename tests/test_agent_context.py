"""Tests for agent context container."""

from langchain_core.messages import HumanMessage

from chaos.engine.agent_context import AgentContext


def test_agent_context_defaults() -> None:
    """Provides default empty context."""
    message = HumanMessage(content="hello")
    context = AgentContext(messages=[message])

    assert context.context == ""
    assert context.messages == [message]
