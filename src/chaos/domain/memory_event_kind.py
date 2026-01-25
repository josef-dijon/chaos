"""Enumerations for memory event classification."""

from enum import Enum


class MemoryEventKind(str, Enum):
    """Defines allowed kinds of idetic memory events."""

    USER_INPUT = "user_input"
    ACTOR_OUTPUT = "actor_output"
    TOOL_CALL = "tool_call"
    TOOL_OUTPUT = "tool_output"
    FEEDBACK = "feedback"
