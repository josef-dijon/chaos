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

    similarity: float = Field(
        default=1.0,
        description="Weight for similarity ranking in STM retrieval scoring.",
        json_schema_extra={"weight": 7},
    )
    recency: float = Field(
        default=1.0,
        description="Weight for recency scoring in STM retrieval.",
        json_schema_extra={"weight": 7},
    )
    kind_boosts: Dict[str, float] = Field(
        default_factory=dict,
        description="Boost multipliers applied per event kind during STM search.",
        json_schema_extra={"weight": 6},
    )
    visibility_boosts: Dict[str, float] = Field(
        default_factory=dict,
        description="Boost multipliers applied per visibility category.",
        json_schema_extra={"weight": 6},
    )

    model_config = ConfigDict(extra="forbid")
