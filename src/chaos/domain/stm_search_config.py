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

    engine: str = Field(default="rapidfuzz", description="Search engine identifier.")
    algorithm: str = Field(default="token_set_ratio", description="Search algorithm.")
    threshold: float = Field(default=60, description="Search similarity threshold.")
    top_k: int = Field(default=8, description="Maximum results to return.")
    recency_half_life_seconds: int = Field(
        default=86400, description="Half-life for recency decay weighting."
    )
    weights: SearchWeights = Field(
        default_factory=SearchWeights, description="Weight tuning for ranking."
    )

    model_config = ConfigDict(extra="forbid")
