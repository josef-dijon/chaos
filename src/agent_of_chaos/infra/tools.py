from agent_of_chaos.domain.tool import BaseTool
from agent_of_chaos.infra.library import Library
from pathlib import Path
from typing import Any, Dict, List, Optional


class FileReadTool(BaseTool):
    name: str = "read_file"
    description: str = "Reads a file from the local filesystem. Args: file_path"

    def run(self, **kwargs: Any) -> str:
        file_path = kwargs.get("file_path")
        if not file_path:
            return "Error: file_path argument is required."
        try:
            return Path(file_path).read_text()
        except Exception as e:
            return f"Error reading file: {e}"


class FileWriteTool(BaseTool):
    name: str = "write_file"
    description: str = "Writes content to a file. Args: file_path, content"

    def run(self, **kwargs: Any) -> str:
        file_path = kwargs.get("file_path")
        content = kwargs.get("content")
        if not file_path or content is None:
            return "Error: file_path and content arguments are required."
        try:
            Path(file_path).write_text(content)
            return "File written successfully."
        except Exception as e:
            return f"Error writing file: {e}"


class ToolLibrary(Library[BaseTool]):
    """
    Central registry for agent tools.
    """

    def __init__(self):
        self._registry: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._registry[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._registry.get(name)

    def list_tools(self) -> List[BaseTool]:
        return list(self._registry.values())

    def filter_tools(
        self,
        whitelist: Optional[List[str]] = None,
        blacklist: Optional[List[str]] = None,
    ) -> List[BaseTool]:
        """
        Returns tools based on access control lists.
        """
        return self.apply_access_control(self.list_tools(), whitelist, blacklist)
