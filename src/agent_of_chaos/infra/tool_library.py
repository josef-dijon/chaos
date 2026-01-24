"""Tool library registry for agent tools."""

from typing import Dict, List, Optional

from agent_of_chaos.domain.tool import BaseTool
from agent_of_chaos.infra.library import Library


class ToolLibrary(Library[BaseTool]):
    """
    Central registry for agent tools.
    """

    def __init__(self) -> None:
        self._registry: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """
        Registers a tool with the library.

        Args:
            tool: The tool instance to register.
        """
        self._registry[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """
        Retrieves a tool by name.

        Args:
            name: The tool name to fetch.

        Returns:
            The matching tool instance or None.
        """
        return self._registry.get(name)

    def list_tools(
        self,
        whitelist: Optional[List[str]] = None,
        blacklist: Optional[List[str]] = None,
    ) -> List[BaseTool]:
        """
        Returns tools filtered by access control lists.

        Args:
            whitelist: Tool names that are allowed.
            blacklist: Tool names that are forbidden.

        Returns:
            The filtered list of tools.
        """
        tools = list(self._registry.values())
        return self.apply_access_control(tools, whitelist, blacklist)
