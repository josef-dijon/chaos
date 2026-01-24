"""Local file read tool implementation."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict

from agent_of_chaos.domain.tool import BaseTool, ToolType


@dataclass
class FileReadTool(BaseTool):
    """
    Reads a file from the local filesystem.
    """

    name: str = "read_file"
    description: str = "Reads a file from the local filesystem."
    type: ToolType = ToolType.CLI
    schema: Dict[str, Any] = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The absolute path to the file",
                }
            },
            "required": ["file_path"],
        }
    )

    def call(self, args: Dict[str, Any]) -> str:
        """
        Executes the file read operation.

        Args:
            args: Tool arguments containing the file_path.

        Returns:
            The file contents or an error message.
        """
        file_path = args.get("file_path")
        if not file_path:
            return "Error: file_path argument is required."
        try:
            return Path(file_path).read_text()
        except Exception as exc:
            return f"Error reading file: {exc}"
