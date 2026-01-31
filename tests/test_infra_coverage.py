import pytest
from unittest.mock import MagicMock, patch

from chaos.config import Config
from chaos.domain.memory_event_kind import MemoryEventKind
from chaos.domain import Identity
from chaos.infra.memory import MemoryContainer


@patch("chaos.infra.memory_container.RawMemoryStore")
@patch("chaos.infra.memory_container.chromadb.PersistentClient")
def test_memory_record_exception(mock_chroma, mock_raw):
    """Return None when raw store writes fail."""
    config = MagicMock(spec=Config)
    config.get_raw_db_path.return_value = "/tmp/raw.db"
    config.get_chroma_db_path.return_value = "/tmp/chroma"
    mock_raw.return_value.record_event.side_effect = Exception("DB Fail")
    mock_collection = MagicMock()
    mock_chroma.return_value.get_or_create_collection.return_value = mock_collection

    identity = Identity.create_default("agent")
    mem = MemoryContainer(agent_id="agent", identity=identity, config=config)

    assert (
        mem.record_event(
            persona="actor",
            loop_id="loop",
            kind=MemoryEventKind.USER_INPUT,
            visibility="external",
            content="content",
        )
        is None
    )


@patch("chaos.infra.memory_container.RawMemoryStore")
@patch("chaos.infra.memory_container.chromadb.PersistentClient")
def test_memory_retrieve_empty_and_exception(mock_chroma, mock_raw):
    """Handle empty, missing, and failing retrievals gracefully."""
    config = MagicMock(spec=Config)
    config.get_raw_db_path.return_value = "/tmp/raw.db"
    config.get_chroma_db_path.return_value = "/tmp/chroma"
    mock_collection = MagicMock()
    mock_chroma.return_value.get_or_create_collection.return_value = mock_collection

    identity = Identity.create_default("agent")
    mem = MemoryContainer(agent_id="agent", identity=identity, config=config)

    # Case: Empty results (documents is empty list)
    mock_collection.query.return_value = {"documents": []}
    assert mem.actor_view().retrieve("q") == []

    # Case: None results (query returns empty dict or None)
    mock_collection.query.return_value = {}
    assert mem.actor_view().retrieve("q") == []

    # Case: Exception
    mock_collection.query.side_effect = Exception("DB Fail")
    assert mem.actor_view().retrieve("q") == []
