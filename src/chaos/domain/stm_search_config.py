from pydantic import BaseModel, ConfigDict, Field

from chaos.domain.search_weights import SearchWeights


class StmSearchConfig(BaseModel):
    """
    Controls the search behavior for short-term memory retrieval.

    Args:
        engine: Search engine identifier.
        algorithm: Search algorithm.
        threshold: Search similarity threshold.
        top_k: Maximum results to return.
        recency_half_life_seconds: Half-life for recency decay weighting.
        weights: Weight tuning for ranking.
    """

    engine: str = Field(
        default="rapidfuzz",
        description="Search engine identifier used for STM retrieval.",
        json_schema_extra={"weight": 6},
    )
    algorithm: str = Field(
        default="token_set_ratio",
        description="Search algorithm name used by the STM search engine.",
        json_schema_extra={"weight": 6},
    )
    threshold: float = Field(
        default=60,
        description=(
            "Similarity threshold for STM matches (0-100). Higher values narrow "
            "results."
        ),
        json_schema_extra={"weight": 7},
    )
    top_k: int = Field(
        default=8,
        description="Maximum number of STM results returned per query.",
        json_schema_extra={"weight": 6},
    )
    recency_half_life_seconds: int = Field(
        default=86400,
        description=(
            "Half-life in seconds for recency decay weighting. Lower values "
            "favor newer memories."
        ),
        json_schema_extra={"weight": 7},
    )
    weights: SearchWeights = Field(
        default_factory=SearchWeights,
        description="Weight tuning for STM ranking components.",
        json_schema_extra={"weight": 7},
    )

    model_config = ConfigDict(extra="forbid")
