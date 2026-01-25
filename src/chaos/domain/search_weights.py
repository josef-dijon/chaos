from typing import Dict

from pydantic import BaseModel, ConfigDict, Field


class SearchWeights(BaseModel):
    """
    Defines weighting configuration for short-term memory searches.

    Args:
        similarity: Weight for similarity ranking.
        recency: Weight for recency scoring.
        kind_boosts: Boosts applied per event kind.
        visibility_boosts: Boosts applied per visibility category.
    """

    similarity: float = Field(default=1.0, description="Weight for similarity ranking.")
    recency: float = Field(default=1.0, description="Weight for recency scoring.")
    kind_boosts: Dict[str, float] = Field(
        default_factory=dict, description="Boosts applied per event kind."
    )
    visibility_boosts: Dict[str, float] = Field(
        default_factory=dict, description="Boosts applied per visibility category."
    )

    model_config = ConfigDict(extra="forbid")
