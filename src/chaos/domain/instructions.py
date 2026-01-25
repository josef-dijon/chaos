from typing import List

from pydantic import BaseModel, ConfigDict, Field


class Instructions(BaseModel):
    """
    Represents the mutable operational instructions of an agent.

    Args:
        operational_notes: Mutable notes learned from experience.
        system_prompts: Base system prompts defining behavior.
    """

    operational_notes: List[str] = Field(
        default_factory=list, description="Mutable notes learned from experience."
    )
    system_prompts: List[str] = Field(
        default_factory=list, description="Base system prompts defining behavior."
    )

    model_config = ConfigDict(extra="forbid")
