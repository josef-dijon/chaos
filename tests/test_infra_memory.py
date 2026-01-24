"""Tests for memory container behavior."""

from unittest.mock import MagicMock, patch

import pytest

from agent_of_chaos.config import Config
from agent_of_chaos.domain.identity import Identity
from agent_of_chaos.infra.memory import MemoryContainer
from agent_of_chaos.infra.raw_memory_store import IdeticEvent


@pytest.fixture
def memory_deps():
    identity = Identity.create_default("agent")
    with (
        patch("agent_of_chaos.infra.memory_container.RawMemoryStore") as mock_raw,
        patch(
            "agent_of_chaos.infra.memory_container.chromadb.PersistentClient"
        ) as mock_chroma,
    ):
        config = MagicMock(spec=Config)
        config.get_raw_db_path.return_value = "/tmp/raw.db"
        config.get_chroma_db_path.return_value = "/tmp/chroma"

        actor_collection = MagicMock()
        subconscious_collection = MagicMock()
        mock_chroma.return_value.get_or_create_collection.side_effect = [
            actor_collection,
            subconscious_collection,
        ]

        yield {
            "identity": identity,
            "raw": mock_raw,
            "chroma": mock_chroma,
            "config": config,
            "actor_collection": actor_collection,
            "subconscious_collection": subconscious_collection,
        }


def test_memory_container_init(memory_deps):
    mem = MemoryContainer(
        agent_id="agent",
        identity=memory_deps["identity"],
        config=memory_deps["config"],
    )

    memory_deps["raw"].assert_called_once_with("/tmp/raw.db")
    memory_deps["chroma"].assert_called_once_with(path="/tmp/chroma")
    memory_deps["chroma"].return_value.get_or_create_collection.assert_any_call(
        name="agent__actor__ltm"
    )
    memory_deps["chroma"].return_value.get_or_create_collection.assert_any_call(
        name="agent__subconscious__ltm"
    )
    assert mem.actor_view()


def test_record_event_updates_vector_store(memory_deps):
    mem = MemoryContainer(
        agent_id="agent",
        identity=memory_deps["identity"],
        config=memory_deps["config"],
    )
    memory_deps["raw"].return_value.record_event.return_value = (
        "event-1",
        "ltm-1",
        "2025-01-01T00:00:00",
    )

    mem.record_event(
        persona="actor",
        loop_id="loop-1",
        kind="user_input",
        visibility="external",
        content="Hello",
        metadata={"source": "unit-test"},
    )

    memory_deps["actor_collection"].upsert.assert_called_once()
    metadata = memory_deps["actor_collection"].upsert.call_args.kwargs["metadatas"][0]
    assert metadata["agent_id"] == "agent"
    assert metadata["persona"] == "actor"
    assert metadata["source"] == "unit-test"
    memory_deps["raw"].return_value.update_ltm_embed_status.assert_called_once_with(
        "ltm-1", "embedded"
    )


def test_record_event_vector_store_error(memory_deps):
    mem = MemoryContainer(
        agent_id="agent",
        identity=memory_deps["identity"],
        config=memory_deps["config"],
    )
    memory_deps["raw"].return_value.record_event.return_value = (
        "event-1",
        "ltm-1",
        "2025-01-01T00:00:00",
    )
    memory_deps["actor_collection"].upsert.side_effect = Exception("fail")

    assert (
        mem.record_event(
            persona="actor",
            loop_id="loop-1",
            kind="user_input",
            visibility="external",
            content="Hello",
        )
        == "ltm-1"
    )


def test_retrieve_for_personas(memory_deps):
    mem = MemoryContainer(
        agent_id="agent",
        identity=memory_deps["identity"],
        config=memory_deps["config"],
    )
    memory_deps["actor_collection"].query.return_value = {"documents": [["doc1"]]}
    memory_deps["subconscious_collection"].query.return_value = {
        "documents": [["doc2"]]
    }

    actor_results = mem.actor_view().retrieve("query")
    subconscious_results = mem.subconscious_view().retrieve("query")

    assert actor_results == ["doc1"]
    assert subconscious_results == ["doc1", "doc2"]
    memory_deps["actor_collection"].query.assert_called_with(
        query_texts=["query"],
        n_results=5,
        where={"agent_id": "agent", "persona": "actor"},
    )
    memory_deps["subconscious_collection"].query.assert_called_with(
        query_texts=["query"],
        n_results=5,
        where={"agent_id": "agent", "persona": "subconscious"},
    )


def test_finalize_loop_creates_summary(memory_deps):
    mem = MemoryContainer(
        agent_id="agent",
        identity=memory_deps["identity"],
        config=memory_deps["config"],
    )
    memory_deps["raw"].return_value.list_idetic_events.return_value = [
        IdeticEvent(
            id="event-1",
            ts="2025-01-01T00:00:00",
            agent_id="agent",
            persona="actor",
            loop_id="loop-1",
            kind="user_input",
            visibility="external",
            content="Hello",
            metadata={},
        ),
        IdeticEvent(
            id="event-2",
            ts="2025-01-01T00:00:01",
            agent_id="agent",
            persona="actor",
            loop_id="loop-1",
            kind="actor_output",
            visibility="external",
            content="Hi",
            metadata={},
        ),
    ]
    memory_deps["raw"].return_value.list_ltm_ids.return_value = [
        "ltm-1",
        "ltm-2",
    ]

    mem.finalize_loop(persona="actor", loop_id="loop-1")

    memory_deps["raw"].return_value.create_stm_entry.assert_called_once()
    args = memory_deps["raw"].return_value.create_stm_entry.call_args.kwargs
    assert args["summary"].startswith("user_input: Hello")


def test_finalize_loop_with_no_events(memory_deps):
    mem = MemoryContainer(
        agent_id="agent",
        identity=memory_deps["identity"],
        config=memory_deps["config"],
    )
    memory_deps["raw"].return_value.list_idetic_events.return_value = []

    mem.finalize_loop(persona="actor", loop_id="loop-1")

    memory_deps["raw"].return_value.create_stm_entry.assert_not_called()


def test_get_recent_stm_as_string(memory_deps):
    mem = MemoryContainer(
        agent_id="agent",
        identity=memory_deps["identity"],
        config=memory_deps["config"],
    )
    memory_deps["raw"].return_value.list_stm_entries.return_value = [
        {
            "id": "stm-1",
            "ts_start": "2025-01-01T00:00:00",
            "ts_end": "2025-01-01T00:00:01",
            "agent_id": "agent",
            "persona": "actor",
            "loop_id": "loop-1",
            "summary": "user_input: Hello",
            "metadata": {},
        }
    ]

    summary = mem.actor_view().get_recent_stm_as_string()

    assert "[actor:loop-1]" in summary


def test_get_recent_stm_as_string_empty(memory_deps):
    mem = MemoryContainer(
        agent_id="agent",
        identity=memory_deps["identity"],
        config=memory_deps["config"],
    )
    memory_deps["raw"].return_value.list_stm_entries.return_value = []

    summary = mem.subconscious_view().get_recent_stm_as_string()

    assert summary == ""


def test_retrieve_unknown_persona(memory_deps):
    mem = MemoryContainer(
        agent_id="agent",
        identity=memory_deps["identity"],
        config=memory_deps["config"],
    )

    assert mem.retrieve_for_personas(["missing"], "query") == []


def test_create_loop_id(memory_deps):
    mem = MemoryContainer(
        agent_id="agent",
        identity=memory_deps["identity"],
        config=memory_deps["config"],
    )

    loop_id = mem.create_loop_id()

    assert isinstance(loop_id, str)
