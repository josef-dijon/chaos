from pydantic import BaseModel, ConfigDict, Field

from agent_of_chaos.domain.stm_search_config import StmSearchConfig


class MemoryPersonaConfig(BaseModel):
    """
    Defines memory configuration for a persona.

    Args:
        ltm_collection: Chroma collection name for long-term memory.
        stm_window_size: Short-term memory window size.
        stm_search: Search configuration for short-term memory.
    """

    ltm_collection: str = Field(
        ..., description="Chroma collection name for long-term memory."
    )
    stm_window_size: int = Field(..., description="Short-term memory window size.")
    stm_search: StmSearchConfig = Field(
        ..., description="Search configuration for short-term memory."
    )

    model_config = ConfigDict(extra="forbid")
