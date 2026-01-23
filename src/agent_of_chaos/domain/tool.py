from abc import ABC, abstractmethod
from typing import Any, Dict
from pydantic import BaseModel, Field


class BaseTool(BaseModel, ABC):
    """
    Abstract base class for all tools in the CHAOS system.
    """

    name: str = Field(..., description="The unique name of the tool.")
    description: str = Field(..., description="Description of what the tool does.")

    @abstractmethod
    def run(self, **kwargs) -> str:
        """
        Executes the tool with the provided arguments.

        Args:
            **kwargs: Arguments for the tool execution.

        Returns:
            The text output of the tool.
        """
        pass
