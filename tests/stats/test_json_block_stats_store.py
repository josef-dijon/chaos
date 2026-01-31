"""Tests for the JSON-backed block stats store."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from chaos.domain.block_estimate import EstimateSource
from chaos.stats.block_attempt_record import BlockAttemptRecord
from chaos.stats.block_stats_identity import BlockStatsIdentity
from chaos.stats.json_block_stats_store import JsonBlockStatsStore


def _build_record(attempt: int = 1) -> BlockAttemptRecord:
    return BlockAttemptRecord(
        trace_id="trace",
        run_id="run",
        span_id="span",
        parent_span_id=None,
        block_name="block",
        block_type="test",
        version=None,
        node_name=None,
        attempt=attempt,
        success=True,
        reason=None,
        error_type=None,
        duration_ms=10.0,
        cost_usd=0.1,
        model=None,
        input_tokens=1,
        output_tokens=2,
        llm_calls=0,
        block_executions=1,
    )


def _build_identity() -> BlockStatsIdentity:
    return BlockStatsIdentity(block_name="block", block_type="test", version=None)


def test_json_store_load_invalid_json(tmp_path: Path) -> None:
    """Invalid JSON content yields empty records."""
    path = tmp_path / "stats.json"
    path.write_text("not json", encoding="utf-8")

    store = JsonBlockStatsStore(path)
    estimate = store.estimate(_build_identity())

    assert estimate.sample_size == 0
    assert estimate.estimate_source == EstimateSource.PRIOR


def test_json_store_load_whitespace(tmp_path: Path) -> None:
    """Empty/whitespace files return no records."""
    path = tmp_path / "stats.json"
    path.write_text("  \n", encoding="utf-8")

    store = JsonBlockStatsStore(path)
    estimate = store.estimate(_build_identity())

    assert estimate.sample_size == 0
    assert estimate.estimate_source == EstimateSource.PRIOR


def test_json_store_load_invalid_format(tmp_path: Path) -> None:
    """Non-list JSON payloads are ignored."""
    path = tmp_path / "stats.json"
    path.write_text(json.dumps({"bad": True}), encoding="utf-8")

    store = JsonBlockStatsStore(path)
    estimate = store.estimate(_build_identity())

    assert estimate.sample_size == 0
    assert estimate.estimate_source == EstimateSource.PRIOR


def test_json_store_load_invalid_list_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Handles unexpected payload types after list detection."""
    path = tmp_path / "stats.json"
    path.write_text(json.dumps({"bad": True}), encoding="utf-8")

    monkeypatch.setattr(
        JsonBlockStatsStore,
        "_peek_first_non_whitespace",
        staticmethod(lambda handle: "["),
    )

    store = JsonBlockStatsStore(path)
    estimate = store.estimate(_build_identity())

    assert estimate.sample_size == 0
    assert estimate.estimate_source == EstimateSource.PRIOR


def test_json_store_load_json_lines(tmp_path: Path) -> None:
    """Loads JSONL records and skips invalid lines."""
    path = tmp_path / "stats.json"
    first = _build_record(attempt=1).model_dump()
    second = _build_record(attempt=2).model_dump()
    path.write_text(
        "\n".join([json.dumps(first), "not json", json.dumps(second)]),
        encoding="utf-8",
    )

    store = JsonBlockStatsStore(path)
    estimate = store.estimate(_build_identity())

    assert estimate.sample_size == 2
    assert estimate.estimate_source == EstimateSource.STATS


def test_json_store_skips_invalid_records_and_retains_latest(tmp_path: Path) -> None:
    """Invalid records are skipped and retention trims history."""
    path = tmp_path / "stats.json"
    valid = _build_record(attempt=1).model_dump()
    payload = [valid, {"bad": "record"}]
    path.write_text(json.dumps(payload), encoding="utf-8")

    store = JsonBlockStatsStore(path, max_records=1)
    assert len(store._records) == 1

    store.record_attempt(_build_record(attempt=2))
    assert len(store._records) == 1

    estimate = store.estimate(_build_identity())
    assert estimate.sample_size == 1


def test_json_store_compacts_on_retention(tmp_path: Path) -> None:
    """Compacts the journal after retention trimming."""
    path = tmp_path / "stats.json"
    store = JsonBlockStatsStore(path, max_records=1)

    store.record_attempt(_build_record(attempt=1))
    store.record_attempt(_build_record(attempt=2))

    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line]
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["attempt"] == 2


def test_json_store_compacts_on_size(tmp_path: Path) -> None:
    """Compacts when the file exceeds the size limit."""
    path = tmp_path / "stats.json"
    store = JsonBlockStatsStore(path, max_records=10, max_file_bytes=1)

    store.record_attempt(_build_record(attempt=1))

    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line]
    assert len(lines) == 1


def test_json_store_compact_stat_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Handles stat failures during compaction checks."""
    path = tmp_path / "stats.json"
    store = JsonBlockStatsStore(path)

    def raise_os_error(self) -> None:
        raise OSError("stat failed")

    monkeypatch.setattr(Path, "stat", raise_os_error)

    assert store._should_compact() is False


def test_json_store_chmod_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """chmod errors are swallowed during save."""
    path = tmp_path / "stats.json"
    store = JsonBlockStatsStore(path)

    def raise_os_error(_: Path, __: int) -> None:
        raise OSError("no perms")

    monkeypatch.setattr("chaos.stats.json_block_stats_store.os.chmod", raise_os_error)

    store.record_attempt(_build_record())
