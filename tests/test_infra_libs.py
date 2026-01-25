import pytest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, call

from chaos.config import Config
from chaos.infra.file_read_tool import MAX_READ_BYTES
from chaos.infra.file_write_tool import MAX_WRITE_BYTES
from chaos.infra.knowledge import KnowledgeLibrary
from chaos.infra.tools import ToolLibrary, FileReadTool, FileWriteTool

# --- KnowledgeLibrary Tests ---


@patch("chaos.infra.knowledge.chromadb.PersistentClient")
def test_knowledge_add_document(mock_chroma):
    mock_collection = MagicMock()
    mock_chroma.return_value.get_or_create_collection.return_value = mock_collection
    config = MagicMock(spec=Config)
    config.get_chroma_db_path.return_value = "/tmp/chroma"

    lib = KnowledgeLibrary(config=config)
    lib.add_document("content", "domainA", {"meta": "data"})

    mock_collection.add.assert_called_once()
    args = mock_collection.add.call_args[1]
    assert args["documents"] == ["content"]
    assert args["metadatas"][0]["domain"] == "domainA"
    assert args["metadatas"][0]["meta"] == "data"


@patch("chaos.infra.knowledge.chromadb.PersistentClient")
def test_knowledge_search(mock_chroma):
    mock_collection = MagicMock()
    mock_chroma.return_value.get_or_create_collection.return_value = mock_collection
    mock_collection.query.return_value = {"documents": [["res1"]]}
    config = MagicMock(spec=Config)
    config.get_chroma_db_path.return_value = "/tmp/chroma"

    lib = KnowledgeLibrary(config=config)

    # Test searches with access control variations
    assert lib.search("q") == ["res1"]
    lib.search("q", whitelist=["d1"])
    lib.search("q", blacklist=["d2"])
    lib.search("q", whitelist=[])

    mock_collection.query.assert_has_calls(
        [
            call(query_texts=["q"], n_results=3, where=None),
            call(query_texts=["q"], n_results=3, where={"domain": {"$in": ["d1"]}}),
            call(query_texts=["q"], n_results=3, where={"domain": {"$nin": ["d2"]}}),
            call(query_texts=["q"], n_results=3, where={"domain": {"$in": []}}),
        ]
    )


@patch("chaos.infra.knowledge.chromadb.PersistentClient")
def test_knowledge_error_handling(mock_chroma):
    mock_collection = MagicMock()
    mock_chroma.return_value.get_or_create_collection.return_value = mock_collection
    mock_collection.add.side_effect = Exception("db error")
    config = MagicMock(spec=Config)
    config.get_chroma_db_path.return_value = "/tmp/chroma"

    lib = KnowledgeLibrary(config=config)
    # Should not raise
    lib.add_document("c", "d")


# --- ToolLibrary Tests ---


def test_tool_library_registry():
    lib = ToolLibrary()
    tool = FileReadTool(root=Path("."))
    lib.register(tool)

    assert lib.get_tool("read_file") == tool
    assert lib.get_tool("missing") is None
    assert len(lib.list_tools()) == 1


def test_tool_library_filter():
    lib = ToolLibrary()
    t1 = FileReadTool(root=Path("."))
    t2 = FileWriteTool(root=Path("."))
    lib.register(t1)
    lib.register(t2)

    # Whitelist
    filtered = lib.list_tools(whitelist=["read_file"])
    assert len(filtered) == 1
    assert filtered[0].name == "read_file"

    # Blacklist
    filtered = lib.list_tools(blacklist=["read_file"])
    assert len(filtered) == 1
    assert filtered[0].name == "write_file"


@patch("pathlib.Path.stat")
@patch("pathlib.Path.read_text")
def test_file_read_tool(mock_read, mock_stat):
    tool = FileReadTool(root=Path("."))
    mock_stat.return_value = SimpleNamespace(st_size=MAX_READ_BYTES)
    mock_read.return_value = "content"

    # Success
    assert tool.call({"file_path": "foo.txt"}) == "content"
    mock_read.assert_called_with()

    # Missing arg
    assert "missing_argument" in tool.call({})

    # Outside root
    assert "path_outside_root" in tool.call({"file_path": "/etc/passwd"})

    # Exception
    mock_read.side_effect = Exception("Error")
    assert "read_failed" in tool.call({"file_path": "foo.txt"})


@patch("pathlib.Path.stat")
def test_file_read_tool_rejects_large_file(mock_stat):
    tool = FileReadTool(root=Path("."))
    mock_stat.return_value = SimpleNamespace(st_size=MAX_READ_BYTES + 1)

    assert "size_limit" in tool.call({"file_path": "foo.txt"})


def test_file_write_tool(tmp_path):
    tool = FileWriteTool(root=tmp_path)

    # Success
    assert "successfully" in tool.call({"file_path": "foo.txt", "content": "bar"})
    assert (tmp_path / "foo.txt").read_text() == "bar"

    # Missing args
    assert "missing_argument" in tool.call({"file_path": "foo.txt"})

    # Outside root
    assert "path_outside_root" in tool.call(
        {"file_path": "/etc/passwd", "content": "x"}
    )


def test_file_write_tool_rejects_large_content():
    tool = FileWriteTool(root=Path("."))
    content = "a" * (MAX_WRITE_BYTES + 1)

    assert "size_limit" in tool.call({"file_path": "foo.txt", "content": content})


@patch("chaos.infra.file_write_tool.tempfile.NamedTemporaryFile")
def test_file_write_tool_handles_temp_error(mock_temp):
    tool = FileWriteTool(root=Path("."))
    mock_temp.side_effect = Exception("Error")

    assert "write_failed" in tool.call({"file_path": "foo.txt", "content": "bar"})
