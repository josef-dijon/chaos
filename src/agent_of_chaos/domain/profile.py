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
        default=None, description="Optional human-friendly display name."
    )
    role: str = Field(..., description="The primary role or function of the agent.")
    core_values: List[str] = Field(
        default_factory=list,
        description="List of core values guiding the agent's behavior.",
    )

    model_config = ConfigDict(extra="forbid")
