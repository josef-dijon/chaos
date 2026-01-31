import json
import logging
import os
from pathlib import Path
from typing import List, Optional

from chaos.domain.block_estimate import BlockEstimate
from chaos.stats.block_attempt_record import BlockAttemptRecord
from chaos.stats.block_stats_identity import BlockStatsIdentity
from chaos.stats.block_stats_store import BlockStatsStore
from chaos.stats.estimate_builder import build_estimate_from_records

logger = logging.getLogger(__name__)


class JsonBlockStatsStore(BlockStatsStore):
    """JSON-backed stats store for block execution attempts."""

    DEFAULT_MAX_RECORDS = 5000
    DEFAULT_MAX_FILE_BYTES = 5_000_000

    def __init__(
        self,
        path: Path,
        max_records: int = DEFAULT_MAX_RECORDS,
        max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    ) -> None:
        """Initialize the store with a JSON file path.

        Args:
            path: Path to the JSON file used for persistence.
            max_records: Maximum number of records to keep in memory/on disk.
            max_file_bytes: Maximum size of the journal before compaction.
        """

        self._path = path
        self._max_records = max(0, int(max_records))
        self._max_file_bytes = max(0, int(max_file_bytes))
        self._records = self._load()
        self._apply_retention()

    def record_attempt(self, record: BlockAttemptRecord) -> None:
        """Record a block execution attempt and persist to JSON.

        Args:
            record: Attempt record to store.
        """

        self._records.append(record)
        trimmed = self._apply_retention()
        self._append_record(record)
        if trimmed or self._should_compact():
            self._compact_records()

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
                first_char = self._peek_first_non_whitespace(handle)
                if first_char is None:
                    return []
                if first_char == "[":
                    payload = json.load(handle)
                    if not isinstance(payload, list):
                        logger.warning(
                            "Block stats file has invalid format; expected list",
                            extra={"path": str(self._path)},
                        )
                        return []
                    return self._parse_payload(payload)
                return self._load_json_lines(handle)
        except (OSError, json.JSONDecodeError):
            logger.warning(
                "Failed to load block stats file; starting with empty records",
                extra={"path": str(self._path)},
            )
            return []

    def _append_record(self, record: BlockAttemptRecord) -> None:
        """Append a record to the journal file."""

        self._path.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(record.model_dump(), sort_keys=True)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(serialized)
            handle.write("\n")
        self._apply_permissions()

    def _compact_records(self) -> None:
        """Rewrite the journal with retained records."""

        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as handle:
            for record in self._records:
                serialized = json.dumps(record.model_dump(), sort_keys=True)
                handle.write(serialized)
                handle.write("\n")
        self._apply_permissions()

    def _apply_permissions(self) -> None:
        """Restrict stats file permissions."""

        try:
            os.chmod(self._path, 0o600)
        except OSError:
            return

    def _apply_retention(self) -> bool:
        """Trim stored records to the configured retention size."""

        if self._max_records <= 0:
            return False
        if len(self._records) <= self._max_records:
            return False
        self._records = self._records[-self._max_records :]
        return True

    def _should_compact(self) -> bool:
        """Return True when the journal should be compacted."""

        if self._max_file_bytes <= 0:
            return False
        try:
            return self._path.stat().st_size > self._max_file_bytes
        except OSError:
            return False

    def _load_json_lines(self, handle) -> List[BlockAttemptRecord]:
        """Load JSONL records from an open handle."""

        records: List[BlockAttemptRecord] = []
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError:
                logger.warning(
                    "Skipping invalid block stats record",
                    extra={"path": str(self._path)},
                )
                continue
            record = self._parse_record(payload)
            if record is not None:
                records.append(record)
        return records

    def _parse_payload(self, payload: List[object]) -> List[BlockAttemptRecord]:
        """Parse a JSON list payload into attempt records."""

        records: List[BlockAttemptRecord] = []
        for item in payload:
            record = self._parse_record(item)
            if record is not None:
                records.append(record)
        return records

    def _parse_record(self, payload: object) -> Optional[BlockAttemptRecord]:
        """Validate a single record payload."""

        try:
            return BlockAttemptRecord.model_validate(payload)
        except Exception:
            logger.warning(
                "Skipping invalid block stats record",
                extra={"path": str(self._path)},
            )
            return None

    @staticmethod
    def _peek_first_non_whitespace(handle) -> Optional[str]:
        """Return the first non-whitespace character in a file."""

        for line in handle:
            for char in line:
                if not char.isspace():
                    handle.seek(0)
                    return char
        handle.seek(0)
        return None
