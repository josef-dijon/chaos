import json
import logging
import os
from pathlib import Path
from typing import List

from chaos.domain.block_estimate import BlockEstimate
from chaos.stats.block_attempt_record import BlockAttemptRecord
from chaos.stats.block_stats_identity import BlockStatsIdentity
from chaos.stats.block_stats_store import BlockStatsStore
from chaos.stats.estimate_builder import build_estimate_from_records

logger = logging.getLogger(__name__)


class JsonBlockStatsStore(BlockStatsStore):
    """JSON-backed stats store for block execution attempts."""

    DEFAULT_MAX_RECORDS = 5000

    def __init__(self, path: Path, max_records: int = DEFAULT_MAX_RECORDS) -> None:
        """Initialize the store with a JSON file path.

        Args:
            path: Path to the JSON file used for persistence.
            max_records: Maximum number of records to keep in memory/on disk.
        """

        self._path = path
        self._max_records = max(0, int(max_records))
        self._records = self._load()
        self._apply_retention()

    def record_attempt(self, record: BlockAttemptRecord) -> None:
        """Record a block execution attempt and persist to JSON.

        Args:
            record: Attempt record to store.
        """

        self._records.append(record)
        self._apply_retention()
        self._save()

    def estimate(self, identity: BlockStatsIdentity) -> BlockEstimate:
        """Estimate execution cost/latency using stored attempts.

        Args:
            identity: Stable block identity metadata.
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
        return build_estimate_from_records(identity, relevant, prior)

    def _load(self) -> List[BlockAttemptRecord]:
        """Load attempt records from disk.

        Returns:
            List of stored attempt records.
        """

        if not self._path.exists():
            return []
        try:
            with self._path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError):
            logger.warning(
                "Failed to load block stats file; starting with empty records",
                extra={"path": str(self._path)},
            )
            return []
        if not isinstance(payload, list):
            logger.warning(
                "Block stats file has invalid format; expected list",
                extra={"path": str(self._path)},
            )
            return []
        records: List[BlockAttemptRecord] = []
        for item in payload:
            try:
                records.append(BlockAttemptRecord.model_validate(item))
            except Exception:
                logger.warning(
                    "Skipping invalid block stats record",
                    extra={"path": str(self._path)},
                )
        return records

    def _save(self) -> None:
        """Persist attempt records to disk."""

        self._path.parent.mkdir(parents=True, exist_ok=True)
        serialized = [record.model_dump() for record in self._records]
        with self._path.open("w", encoding="utf-8") as handle:
            json.dump(serialized, handle, indent=2, sort_keys=True)
        try:
            os.chmod(self._path, 0o600)
        except OSError:
            return

    def _apply_retention(self) -> None:
        """Trim stored records to the configured retention size."""

        if self._max_records <= 0:
            return
        if len(self._records) <= self._max_records:
            return
        self._records = self._records[-self._max_records :]
