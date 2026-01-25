from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict


class ToolType(str, Enum):
    """
    Enumerates supported tool execution types.
    """

    CLI = "CLI"
    MCP = "MCP"


@dataclass
class BaseTool(ABC):
    """
    Abstract base class for all tools in the CHAOS system.
    """

    name: str
    description: str
    type: ToolType
    schema: Dict[str, Any]

    @abstractmethod
    def call(self, args: Dict[str, Any]) -> str:
        """
        Executes the tool with the provided arguments.

        Args:
            args: Arguments for the tool execution.

        Returns:
            The text output of the tool.
        """
        raise NotImplementedError

    def as_openai_tool(self) -> Dict[str, Any]:
        """
        Returns an OpenAI-compatible tool schema definition.

        Returns:
            A dictionary describing the tool for LLM binding.
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.schema,
            },
        }
