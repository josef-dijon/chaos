"""Typed container for agent loop inputs and outputs."""

from dataclasses import dataclass
from typing import List

from langchain_core.messages import BaseMessage


@dataclass(frozen=True)
class AgentContext:
    """
    Represents agent loop state passed between steps.

    Args:
        messages: The conversation messages for the loop.
        context: Retrieved context to guide reasoning.
    """

    messages: List[BaseMessage]
    context: str = ""
