"""Local file read tool implementation."""

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Dict

from chaos.domain.tool import BaseTool, ToolType

MAX_READ_BYTES = 1_000_000


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
    root: Path = field(default_factory=Path.cwd)

    def _resolve_path(self, file_path: str) -> Path:
        """
        Resolves a file path and validates it against the allowed root.

        Args:
            file_path: The requested file path.

        Returns:
            The resolved file path.
        """
        root = self.root.expanduser().resolve()
        candidate = Path(file_path).expanduser()
        if not candidate.is_absolute():
            candidate = (root / candidate).resolve()
        else:
            candidate = candidate.resolve()

        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise ValueError(
                f"Error: file_path is outside allowed root {root}."
            ) from exc

        restricted_root = root / ".chaos" / "identities"
        try:
            candidate.relative_to(restricted_root)
            raise ValueError("Error: file_path targets a restricted identity file.")
        except ValueError as exc:
            if "restricted identity" in str(exc):
                raise

        return candidate

    def _error(self, code: str, message: str) -> str:
        """
        Formats an error payload for tool responses.

        Args:
            code: Machine-readable error code.
            message: Human-readable error message.

        Returns:
            A JSON error payload string.
        """
        return json.dumps({"error": {"code": code, "message": message}})

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
            return self._error("missing_argument", "file_path is required")
        try:
            resolved_path = self._resolve_path(file_path)
            if resolved_path.stat().st_size > MAX_READ_BYTES:
                return self._error(
                    "size_limit",
                    f"file exceeds max size of {MAX_READ_BYTES} bytes",
                )
            return resolved_path.read_text()
        except ValueError as exc:
            return self._error("path_outside_root", str(exc))
        except Exception as exc:
            return self._error("read_failed", str(exc))
