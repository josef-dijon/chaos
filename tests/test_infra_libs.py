import pytest
from unittest.mock import MagicMock, patch, call

from agent_of_chaos.config import Config
from agent_of_chaos.infra.knowledge import KnowledgeLibrary
from agent_of_chaos.infra.tools import ToolLibrary, FileReadTool, FileWriteTool

# --- KnowledgeLibrary Tests ---


@patch("agent_of_chaos.infra.knowledge.chromadb.PersistentClient")
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


@patch("agent_of_chaos.infra.knowledge.chromadb.PersistentClient")
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


@patch("agent_of_chaos.infra.knowledge.chromadb.PersistentClient")
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
    tool = FileReadTool()
    lib.register(tool)

    assert lib.get_tool("read_file") == tool
    assert lib.get_tool("missing") is None
    assert len(lib.list_tools()) == 1


def test_tool_library_filter():
    lib = ToolLibrary()
    t1 = FileReadTool()
    t2 = FileWriteTool()
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


@patch("pathlib.Path.read_text")
def test_file_read_tool(mock_read):
    tool = FileReadTool()
    mock_read.return_value = "content"

    # Success
    assert tool.call({"file_path": "foo.txt"}) == "content"
    mock_read.assert_called_with()

    # Missing arg
    assert "required" in tool.call({})

    # Exception
    mock_read.side_effect = Exception("Error")
    assert "Error" in tool.call({"file_path": "foo.txt"})


@patch("pathlib.Path.write_text")
def test_file_write_tool(mock_write):
    tool = FileWriteTool()

    # Success
    assert "successfully" in tool.call({"file_path": "foo.txt", "content": "bar"})
    mock_write.assert_called_with("bar")

    # Missing args
    assert "required" in tool.call({"file_path": "foo.txt"})

    # Exception
    mock_write.side_effect = Exception("Error")
    assert "Error" in tool.call({"file_path": "foo.txt", "content": "bar"})
