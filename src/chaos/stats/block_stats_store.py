from abc import ABC, abstractmethod

from chaos.domain.block_estimate import BlockEstimate
from chaos.stats.block_attempt_record import BlockAttemptRecord
from chaos.stats.block_stats_identity import BlockStatsIdentity


class BlockStatsStore(ABC):
    """Interface for recording attempts and querying block estimates."""

    @abstractmethod
    def record_attempt(self, record: BlockAttemptRecord) -> None:
        """Record a single block execution attempt.

        Args:
            record: Attempt record to persist.
        """

    @abstractmethod
    def estimate(self, identity: BlockStatsIdentity) -> BlockEstimate:
        """Estimate execution cost/latency for a block.

        Args:
            identity: Stable block identity metadata.
        Returns:
            A BlockEstimate for the given request.
        """
