from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class Profile(BaseModel):
    """
    Represents the immutable core description of an agent.

    Args:
        name: Optional human-friendly display name.
        role: The primary role or function of the agent.
        core_values: List of core values guiding the agent's behavior.
    """

    name: Optional[str] = Field(
        default=None,
        description=(
            "Optional human-friendly display name used in prompts. If omitted, "
            "the agent_id-derived name is used."
        ),
        json_schema_extra={"weight": 6},
    )
    role: str = Field(
        ...,
        description=(
            "Primary role or function of the agent. This anchors task framing and "
            "should only change with deliberate intent."
        ),
        json_schema_extra={"weight": 9},
    )
    core_values: List[str] = Field(
        default_factory=list,
        description=(
            "List of core values that guide behavior across all tasks. Treat as "
            "high-stability principles."
        ),
        json_schema_extra={"weight": 9},
    )

    model_config = ConfigDict(extra="forbid")
