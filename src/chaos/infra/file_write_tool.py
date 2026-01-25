"""Local file write tool implementation."""

from dataclasses import dataclass, field
import json
from pathlib import Path
import tempfile
from typing import Any, Dict

from chaos.domain.tool import BaseTool, ToolType

MAX_WRITE_BYTES = 1_000_000


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
        Executes the file write operation.

        Args:
            args: Tool arguments containing file_path and content.

        Returns:
            A success or error message.
        """
        file_path = args.get("file_path")
        content = args.get("content")
        if not file_path or content is None:
            return self._error("missing_argument", "file_path and content are required")
        try:
            resolved_path = self._resolve_path(file_path)
            content_bytes = len(content.encode("utf-8"))
            if content_bytes > MAX_WRITE_BYTES:
                return self._error(
                    "size_limit",
                    f"content exceeds max size of {MAX_WRITE_BYTES} bytes",
                )
            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(
                    delete=False,
                    dir=resolved_path.parent,
                    mode="w",
                    encoding="utf-8",
                ) as tmp_file:
                    tmp_file.write(content)
                    temp_path = Path(tmp_file.name)
                temp_path.replace(resolved_path)
                return "File written successfully."
            except Exception as exc:
                if temp_path and temp_path.exists():
                    temp_path.unlink()
                return self._error("write_failed", str(exc))
        except ValueError as exc:
            return self._error("path_outside_root", str(exc))
        except Exception as exc:
            return self._error("write_failed", str(exc))
