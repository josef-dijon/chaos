from chaos.domain.block_estimate import BlockEstimate, EstimateSource
from chaos.stats.block_stats_identity import BlockStatsIdentity
from chaos.stats.block_stats_store import BlockStatsStore


class LiteLLMStatsAdapter:
    """Adapter for LiteLLM stats integration."""

    def __init__(self, store: BlockStatsStore) -> None:
        """Initialize the adapter.

        Args:
            store: Stats store used for estimation.
        """

        self._store = store

    def estimate(
        self,
        identity: BlockStatsIdentity,
        prior: BlockEstimate,
    ) -> BlockEstimate:
        """Estimate LLM execution metrics using the stats store.

        Args:
            identity: Stable block identity metadata.
            prior: Prior estimate to fall back on.

        Returns:
            A BlockEstimate derived from stats or the provided prior.
        """

        estimate = self._store.estimate(identity)
        if (
            estimate.estimate_source == EstimateSource.PRIOR
            or estimate.sample_size == 0
        ):
            return prior
        return estimate
