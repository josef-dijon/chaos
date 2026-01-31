from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from chaos.stats.block_stats_identity import BlockStatsIdentity


class EstimateSource(str, Enum):
    """Allowed sources for block estimates."""

    STATS = "stats"
    PRIOR = "prior"
    HEURISTIC = "heuristic"
    UNKNOWN = "unknown"


class EstimateConfidence(str, Enum):
    """Allowed confidence levels for block estimates."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class BlockEstimate(BaseModel):
    """Structured estimate of a block's expected execution footprint."""

    block_name: str = Field(description="Stable block instance name.")
    block_type: str = Field(description="Stable block type identifier.")
    version: Optional[str] = Field(default=None, description="Optional block version.")
    estimate_source: EstimateSource = Field(
        description="Source of the estimate: stats, prior, heuristic, or unknown."
    )
    confidence: EstimateConfidence = Field(
        description="Confidence level: low, medium, or high."
    )
    sample_size: int = Field(description="Number of samples used for the estimate.")
    time_ms_mean: float = Field(description="Mean estimated duration in milliseconds.")
    time_ms_std: float = Field(
        description="Standard deviation of estimated duration in milliseconds."
    )
    cost_usd_mean: float = Field(description="Mean estimated cost in USD.")
    cost_usd_std: float = Field(
        description="Standard deviation of estimated cost in USD."
    )
    expected_llm_calls: float = Field(
        description="Expected number of LLM calls made by the block."
    )
    expected_block_executions: float = Field(
        description="Expected number of block executions for this block."
    )
    components: Optional[dict[str, "BlockEstimate"]] = Field(
        default=None, description="Optional component estimate breakdown."
    )
    notes: List[str] = Field(
        default_factory=list, description="Assumptions or estimation notes."
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def from_prior(
        cls,
        identity: BlockStatsIdentity,
        time_ms_mean: float = 10.0,
        time_ms_std: float = 5.0,
        cost_usd_mean: float = 0.0,
        cost_usd_std: float = 0.0,
        expected_llm_calls: float = 0.0,
        expected_block_executions: float = 1.0,
        notes: Optional[List[str]] = None,
    ) -> "BlockEstimate":
        """Build a conservative prior estimate for a block.

        Args:
            identity: Stable block identity metadata.
            time_ms_mean: Prior mean for duration in milliseconds.
            time_ms_std: Prior standard deviation for duration in milliseconds.
            cost_usd_mean: Prior mean for cost in USD.
            cost_usd_std: Prior standard deviation for cost in USD.
            expected_llm_calls: Prior expected count of LLM calls.
            expected_block_executions: Prior expected count of block executions.
            notes: Optional notes describing assumptions.

        Returns:
            A BlockEstimate populated with prior values.
        """

        return cls(
            block_name=identity.block_name,
            block_type=identity.block_type,
            version=identity.version,
            estimate_source=EstimateSource.PRIOR,
            confidence=EstimateConfidence.LOW,
            sample_size=0,
            time_ms_mean=time_ms_mean,
            time_ms_std=time_ms_std,
            cost_usd_mean=cost_usd_mean,
            cost_usd_std=cost_usd_std,
            expected_llm_calls=expected_llm_calls,
            expected_block_executions=expected_block_executions,
            notes=notes or [],
        )


BlockEstimate.model_rebuild()
