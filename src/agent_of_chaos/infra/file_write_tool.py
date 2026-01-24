"""Local file write tool implementation."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict

from agent_of_chaos.domain.tool import BaseTool, ToolType


@dataclass
class FileWriteTool(BaseTool):
    """
    Writes content to a file on the local filesystem.
    """

    name: str = "write_file"
    description: str = "Writes content to a file."
    type: ToolType = ToolType.CLI
    schema: Dict[str, Any] = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The absolute path to the file",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file",
                },
            },
            "required": ["file_path", "content"],
        }
    )

    def call(self, args: Dict[str, Any]) -> str:
        """
        Executes the file write operation.

        Args:
            args: Tool arguments containing file_path and content.

        Returns:
            A success or error message.
        """
        file_path = args.get("file_path")
        content = args.get("content")
        if not file_path or content is None:
            return "Error: file_path and content arguments are required."
        try:
            Path(file_path).write_text(content)
            return "File written successfully."
        except Exception as exc:
            return f"Error writing file: {exc}"
