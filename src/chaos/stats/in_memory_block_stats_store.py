from typing import List

from chaos.domain.block_estimate import BlockEstimate
from chaos.stats.block_attempt_record import BlockAttemptRecord
from chaos.stats.block_stats_identity import BlockStatsIdentity
from chaos.stats.block_stats_store import BlockStatsStore
from chaos.stats.estimate_builder import build_estimate_from_records


class InMemoryBlockStatsStore(BlockStatsStore):
    """In-memory stats store for block execution attempts."""

    def __init__(self) -> None:
        """Initialize an empty in-memory stats store."""

        self._records: List[BlockAttemptRecord] = []

    def record_attempt(self, record: BlockAttemptRecord) -> None:
        """Record a block execution attempt.

        Args:
            record: Attempt record to store.
        """

        self._records.append(record)

    def estimate(self, identity: BlockStatsIdentity) -> BlockEstimate:
        """Estimate execution cost/latency using stored attempts.

        Args:
            identity: Stable block identity metadata.
        Returns:
            A BlockEstimate based on in-memory records.
        """

        relevant = [
            record
            for record in self._records
            if record.block_name == identity.block_name
            and record.block_type == identity.block_type
            and record.version == identity.version
        ]
        prior = BlockEstimate.from_prior(identity)
        return build_estimate_from_records(identity, relevant, prior)
