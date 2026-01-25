from pydantic import BaseModel, ConfigDict, Field

from chaos.domain.stm_search_config import StmSearchConfig


class MemoryPersonaConfig(BaseModel):
    """
    Defines memory configuration for a persona.

    Args:
        ltm_collection: Chroma collection name for long-term memory.
        stm_window_size: Short-term memory window size.
        stm_search: Search configuration for short-term memory.
    """

    ltm_collection: str = Field(
        ...,
        description=(
            "Chroma collection name for long-term memory embeddings. This should "
            "stay stable to preserve memory continuity."
        ),
        json_schema_extra={"weight": 9},
    )
    stm_window_size: int = Field(
        ...,
        description=(
            "Short-term memory window size in loops. Larger values retain more "
            "recent interactions."
        ),
        json_schema_extra={"weight": 6},
    )
    stm_search: StmSearchConfig = Field(
        ...,
        description=(
            "Search configuration for short-term memory retrieval, including "
            "similarity thresholds and weighting."
        ),
        json_schema_extra={"weight": 7},
    )

    model_config = ConfigDict(extra="forbid")
