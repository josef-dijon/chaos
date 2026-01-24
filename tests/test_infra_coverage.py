import pytest
from unittest.mock import MagicMock, patch

from agent_of_chaos.domain.identity import Identity
from agent_of_chaos.infra.memory import MemoryContainer


@patch("agent_of_chaos.infra.memory_container.RawMemoryStore")
@patch("agent_of_chaos.infra.memory_container.chromadb.PersistentClient")
@patch("agent_of_chaos.infra.memory_container.settings")
def test_memory_record_exception(mock_settings, mock_chroma, mock_raw):
    mock_settings.get_raw_db_path.return_value = "/tmp/raw.db"
    mock_settings.get_chroma_db_path.return_value = "/tmp/chroma"
    mock_raw.return_value.record_event.side_effect = Exception("DB Fail")
    mock_collection = MagicMock()
    mock_chroma.return_value.get_or_create_collection.return_value = mock_collection

    identity = Identity.create_default("agent")
    mem = MemoryContainer(agent_id="agent", identity=identity)

    assert (
        mem.record_event(
            persona="actor",
            loop_id="loop",
            kind="user_input",
            visibility="external",
            content="content",
        )
        is None
    )


@patch("agent_of_chaos.infra.memory_container.RawMemoryStore")
@patch("agent_of_chaos.infra.memory_container.chromadb.PersistentClient")
@patch("agent_of_chaos.infra.memory_container.settings")
def test_memory_retrieve_empty_and_exception(mock_settings, mock_chroma, mock_raw):
    mock_settings.get_raw_db_path.return_value = "/tmp/raw.db"
    mock_settings.get_chroma_db_path.return_value = "/tmp/chroma"
    mock_collection = MagicMock()
    mock_chroma.return_value.get_or_create_collection.return_value = mock_collection

    identity = Identity.create_default("agent")
    mem = MemoryContainer(agent_id="agent", identity=identity)

    # Case: Empty results (documents is empty list)
    mock_collection.query.return_value = {"documents": []}
    assert mem.actor_view().retrieve("q") == []

    # Case: None results (query returns empty dict or None)
    mock_collection.query.return_value = {}
    assert mem.actor_view().retrieve("q") == []

    # Case: Exception
    mock_collection.query.side_effect = Exception("DB Fail")
    assert mem.actor_view().retrieve("q") == []
