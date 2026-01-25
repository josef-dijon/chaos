"""Tool execution utilities for agent loops."""

from typing import Any, List, Mapping, Sequence

from langchain_core.messages import ToolMessage

from chaos.infra.tools import ToolLibrary


class ToolRunner:
    """
    Executes tool calls using a configured tool library.

    Args:
        tool_lib: The tool library used to resolve tool calls.
    """

    def __init__(self, tool_lib: ToolLibrary) -> None:
        self.tool_lib = tool_lib

    def run(self, tool_calls: Sequence[Mapping[str, Any]]) -> List[ToolMessage]:
        """
        Executes tool calls and returns tool messages.

        Args:
            tool_calls: Tool call payloads emitted by the LLM.

        Returns:
            ToolMessage instances containing tool outputs.
        """
        results: List[ToolMessage] = []
        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_id = tool_call["id"]

            tool = self.tool_lib.get_tool(tool_name)
            if tool:
                try:
                    output = tool.call(tool_args)
                except Exception as exc:
                    output = f"Error executing {tool_name}: {exc}"
            else:
                output = f"Error: Tool {tool_name} not found or access denied."

            results.append(
                ToolMessage(content=output, tool_call_id=tool_id, name=tool_name)
            )

        return results
