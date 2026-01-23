import pytest
from unittest.mock import MagicMock, patch
from agent_of_chaos.infra.memory import MemoryContainer


@pytest.fixture
def mock_deps():
    with (
        patch("agent_of_chaos.infra.memory.chromadb.PersistentClient") as mock_chroma,
        patch("agent_of_chaos.infra.memory.settings") as mock_settings,
    ):
        mock_settings.chroma_db_path = "/tmp/db"
        mock_collection = MagicMock()
        mock_chroma.return_value.get_or_create_collection.return_value = mock_collection

        yield {
            "chroma": mock_chroma,
            "settings": mock_settings,
            "collection": mock_collection,
        }


def test_memory_container_init(mock_deps):
    mem = MemoryContainer()
    mock_deps["chroma"].assert_called_once_with(path="/tmp/db")
    mock_deps["chroma"].return_value.get_or_create_collection.assert_called_with(
        name="agent_memories"
    )


def test_memory_record(mock_deps):
    mem = MemoryContainer()
    mem.record("user", "Hello")

    # Check STM
    assert len(mem.stm) == 1
    assert mem.stm[0]["role"] == "user"
    assert mem.stm[0]["content"] == "Hello"

    # Check LTM
    mock_deps["collection"].add.assert_called_once()
    call_args = mock_deps["collection"].add.call_args[1]
    assert call_args["documents"] == ["Hello"]
    assert call_args["metadatas"][0]["role"] == "user"


def test_memory_retrieve(mock_deps):
    mock_deps["collection"].query.return_value = {"documents": [["doc1", "doc2"]]}

    mem = MemoryContainer()
    results = mem.retrieve("test query")

    assert results == ["doc1", "doc2"]
    mock_deps["collection"].query.assert_called_with(
        query_texts=["test query"], n_results=5, where=None
    )


def test_get_stm_as_string(mock_deps):
    mem = MemoryContainer()
    mem.record("user", "Hi")
    mem.record("assistant", "Hello")

    s = mem.get_stm_as_string()
    assert "user: Hi" in s
    assert "assistant: Hello" in s
