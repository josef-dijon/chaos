import json
from pathlib import Path
from typing import List

from chaos.domain.block_estimate import BlockEstimate
from chaos.domain.messages import Request
from chaos.stats.block_attempt_record import BlockAttemptRecord
from chaos.stats.block_stats_identity import BlockStatsIdentity
from chaos.stats.block_stats_store import BlockStatsStore
from chaos.stats.estimate_builder import build_estimate_from_records


class JsonBlockStatsStore(BlockStatsStore):
    """JSON-backed stats store for block execution attempts."""

    def __init__(self, path: Path) -> None:
        """Initialize the store with a JSON file path.

        Args:
            path: Path to the JSON file used for persistence.
        """

        self._path = path
        self._records = self._load()

    def record_attempt(self, record: BlockAttemptRecord) -> None:
        """Record a block execution attempt and persist to JSON.

        Args:
            record: Attempt record to store.
        """

        self._records.append(record)
        self._save()

    def estimate(self, identity: BlockStatsIdentity, request: Request) -> BlockEstimate:
        """Estimate execution cost/latency using stored attempts.

        Args:
            identity: Stable block identity metadata.
            request: Request to be estimated.

        Returns:
            A BlockEstimate based on JSON records.
        """

        relevant = [
            record
            for record in self._records
            if record.block_name == identity.block_name
            and record.block_type == identity.block_type
            and record.version == identity.version
        ]
        prior = BlockEstimate.from_prior(identity)
        return build_estimate_from_records(identity, request, relevant, prior)

    def _load(self) -> List[BlockAttemptRecord]:
        """Load attempt records from disk.

        Returns:
            List of stored attempt records.
        """

        if not self._path.exists():
            return []
        with self._path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return [BlockAttemptRecord.model_validate(item) for item in payload]

    def _save(self) -> None:
        """Persist attempt records to disk."""

        self._path.parent.mkdir(parents=True, exist_ok=True)
        serialized = [record.model_dump() for record in self._records]
        with self._path.open("w", encoding="utf-8") as handle:
            json.dump(serialized, handle, indent=2, sort_keys=True)
