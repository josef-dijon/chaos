from typing import Dict, List, Optional, Tuple

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
        self._index: Dict[Tuple[str, str, Optional[str]], List[BlockAttemptRecord]] = {}

    def record_attempt(self, record: BlockAttemptRecord) -> None:
        """Record a block execution attempt.

        Args:
            record: Attempt record to store.
        """

        self._records.append(record)
        self._add_to_index(record)

    def estimate(self, identity: BlockStatsIdentity) -> BlockEstimate:
        """Estimate execution cost/latency using stored attempts.

        Args:
            identity: Stable block identity metadata.
        Returns:
            A BlockEstimate based on in-memory records.
        """

        relevant = self._index.get(self._identity_key(identity), [])
        prior = BlockEstimate.from_prior(identity)
        return build_estimate_from_records(identity, relevant, prior)

    def _add_to_index(self, record: BlockAttemptRecord) -> None:
        """Add a record to the in-memory index."""

        key = self._record_key(record)
        self._index.setdefault(key, []).append(record)

    @staticmethod
    def _record_key(
        record: BlockAttemptRecord,
    ) -> Tuple[str, str, Optional[str]]:
        """Build a dictionary key for a record."""

        return (record.block_name, record.block_type, record.version)

    @staticmethod
    def _identity_key(
        identity: BlockStatsIdentity,
    ) -> Tuple[str, str, Optional[str]]:
        """Build a dictionary key for an identity."""

        return (identity.block_name, identity.block_type, identity.version)
