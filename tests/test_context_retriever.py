"""Tests for context retrieval utilities."""

from unittest.mock import MagicMock

from langchain_core.messages import HumanMessage

from chaos.domain import Identity
from chaos.engine.context_retriever import ContextRetriever


def test_retrieve_returns_empty_without_messages() -> None:
    """Returns empty context when no messages exist."""
    identity = Identity.create_default(agent_id="tester")
    memory = MagicMock()
    knowledge = MagicMock()

    retriever = ContextRetriever(identity, memory, knowledge, persona="actor")

    assert retriever.retrieve([]) == ""


def test_retrieve_includes_ltm_and_knowledge() -> None:
    """Includes LTM and knowledge when available."""
    identity = Identity.create_default(agent_id="tester")
    identity.knowledge_whitelist = ["allowed"]
    identity.knowledge_blacklist = ["blocked"]
    memory = MagicMock()
    knowledge = MagicMock()
    memory.retrieve.return_value = "facts"
    knowledge.search.return_value = "ref"

    retriever = ContextRetriever(identity, memory, knowledge, persona="actor")
    context = retriever.retrieve([HumanMessage(content="query")])

    assert "LTM: facts" in context
    assert "Reference Knowledge: ref" in context
    knowledge.search.assert_called_once_with(
        query="query",
        whitelist=["allowed"],
        blacklist=["blocked"],
    )


def test_subconscious_ignores_knowledge_filters() -> None:
    """Uses unrestricted knowledge access for the subconscious persona."""
    identity = Identity.create_default(agent_id="tester")
    identity.knowledge_whitelist = ["allowed"]
    identity.knowledge_blacklist = ["blocked"]
    memory = MagicMock()
    knowledge = MagicMock()
    memory.retrieve.return_value = "facts"
    knowledge.search.return_value = "ref"

    retriever = ContextRetriever(identity, memory, knowledge, persona="subconscious")
    retriever.retrieve([HumanMessage(content="query")])

    knowledge.search.assert_called_once_with(
        query="query",
        whitelist=None,
        blacklist=None,
    )
