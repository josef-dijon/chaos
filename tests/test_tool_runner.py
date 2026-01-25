"""Tests for tool execution utilities."""

from unittest.mock import MagicMock

from chaos.engine.tool_runner import ToolRunner


def test_run_executes_tool_call() -> None:
    """Executes tool calls and returns tool messages."""
    tool = MagicMock()
    tool.call.return_value = "ok"
    tool_lib = MagicMock()
    tool_lib.get_tool.return_value = tool
    runner = ToolRunner(tool_lib)

    results = runner.run([{"name": "demo", "args": {"a": 1}, "id": "t1"}])

    assert results[0].content == "ok"
    assert results[0].name == "demo"


def test_run_handles_missing_tool() -> None:
    """Returns error message when tool is not found."""
    tool_lib = MagicMock()
    tool_lib.get_tool.return_value = None
    runner = ToolRunner(tool_lib)

    results = runner.run([{"name": "missing", "args": {}, "id": "t1"}])

    assert "not found" in results[0].content


def test_run_handles_tool_error() -> None:
    """Returns error output when tool execution raises."""
    tool = MagicMock()
    tool.call.side_effect = RuntimeError("boom")
    tool_lib = MagicMock()
    tool_lib.get_tool.return_value = tool
    runner = ToolRunner(tool_lib)

    results = runner.run([{"name": "demo", "args": {}, "id": "t1"}])

    assert "Error executing demo" in results[0].content
