import pytest
from unittest.mock import MagicMock, patch
from agent_of_chaos.infra.memory import MemoryContainer


@patch("agent_of_chaos.infra.memory.chromadb.PersistentClient")
@patch("agent_of_chaos.infra.memory.settings")
def test_memory_record_exception(mock_settings, mock_chroma):
    mock_collection = MagicMock()
    mock_chroma.return_value.get_or_create_collection.return_value = mock_collection
    mock_collection.add.side_effect = Exception("DB Fail")

    mem = MemoryContainer()
    # Should not raise, just log error
    mem.record("user", "content")


@patch("agent_of_chaos.infra.memory.chromadb.PersistentClient")
@patch("agent_of_chaos.infra.memory.settings")
def test_memory_retrieve_empty_and_exception(mock_settings, mock_chroma):
    mock_collection = MagicMock()
    mock_chroma.return_value.get_or_create_collection.return_value = mock_collection

    mem = MemoryContainer()

    # Case: Empty results (documents is empty list)
    mock_collection.query.return_value = {"documents": []}
    assert mem.retrieve("q") == []

    # Case: None results (query returns empty dict or None)
    mock_collection.query.return_value = {}
    assert mem.retrieve("q") == []

    # Case: Exception
    mock_collection.query.side_effect = Exception("DB Fail")
    assert mem.retrieve("q") == []
