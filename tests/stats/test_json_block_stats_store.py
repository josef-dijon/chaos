"""Tests for the JSON-backed block stats store."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from chaos.domain.messages import Request
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
    estimate = store.estimate(_build_identity(), Request())

    assert estimate.sample_size == 0
    assert estimate.estimate_source == "prior"


def test_json_store_load_invalid_format(tmp_path: Path) -> None:
    """Non-list JSON payloads are ignored."""
    path = tmp_path / "stats.json"
    path.write_text(json.dumps({"bad": True}), encoding="utf-8")

    store = JsonBlockStatsStore(path)
    estimate = store.estimate(_build_identity(), Request())

    assert estimate.sample_size == 0
    assert estimate.estimate_source == "prior"


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

    estimate = store.estimate(_build_identity(), Request())
    assert estimate.sample_size == 1


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
