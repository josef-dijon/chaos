"""Tests for the raw memory SQLite store."""

from pathlib import Path
from unittest.mock import MagicMock

from chaos.domain.memory_event_kind import MemoryEventKind
from chaos.infra.raw_memory_store import RawMemoryStore


def test_raw_memory_store_records_events(tmp_path: Path) -> None:
    """Records events and returns IDs from the raw store."""
    db_path = tmp_path / "raw.sqlite"
    with RawMemoryStore(db_path) as store:
        store._ensure_schema_version()
        event_id, ltm_id, ts = store.record_event(
            agent_id="agent",
            persona="actor",
            loop_id="loop-1",
            kind=MemoryEventKind.USER_INPUT,
            visibility="external",
            content="Hello",
        )

        events = store.list_idetic_events(
            agent_id="agent", personas=["actor"], loop_id="loop-1"
        )
        assert len(events) == 1
        assert events[0].id == event_id
        assert events[0].ts == ts

        ltm_ids = store.list_ltm_ids(
            agent_id="agent", persona="actor", loop_id="loop-1"
        )
        assert ltm_ids == [ltm_id]


def test_raw_memory_store_stm_entries(tmp_path: Path) -> None:
    """Creates and retrieves STM entries."""
    db_path = tmp_path / "raw.sqlite"
    with RawMemoryStore(db_path) as store:
        store.record_event(
            agent_id="agent",
            persona="actor",
            loop_id="loop-1",
            kind=MemoryEventKind.USER_INPUT,
            visibility="external",
            content="Hello",
        )
        store.record_event(
            agent_id="agent",
            persona="actor",
            loop_id="loop-1",
            kind=MemoryEventKind.ACTOR_OUTPUT,
            visibility="external",
            content="Hi",
        )

        events = store.list_idetic_events(
            agent_id="agent", personas=["actor"], loop_id="loop-1"
        )
        ltm_ids = store.list_ltm_ids(
            agent_id="agent", persona="actor", loop_id="loop-1"
        )

        store.create_stm_entry(
            agent_id="agent",
            persona="actor",
            loop_id="loop-1",
            summary="user_input: Hello\nactor_output: Hi",
            ts_start=events[0].ts,
            ts_end=events[-1].ts,
            ltm_ids=ltm_ids,
        )
        store.create_stm_entry(
            agent_id="agent",
            persona="actor",
            loop_id="loop-1",
            summary="user_input: Hello\nactor_output: Hi",
            ts_start=events[0].ts,
            ts_end=events[-1].ts,
            ltm_ids=ltm_ids,
        )

        entries = store.list_stm_entries(agent_id="agent", personas=["actor"], limit=1)
        assert entries[0]["summary"].startswith("user_input: Hello")


def test_raw_memory_store_close(tmp_path: Path) -> None:
    """Closes the underlying connection."""
    db_path = tmp_path / "raw.sqlite"
    store = RawMemoryStore(db_path)
    store.connection.close()
    store.connection = MagicMock()

    store.close()

    store.connection.close.assert_called_once()


def test_raw_memory_store_empty_queries(tmp_path: Path) -> None:
    """Returns empty lists for empty persona queries."""
    db_path = tmp_path / "raw.sqlite"
    with RawMemoryStore(db_path) as store:
        assert (
            store.list_idetic_events(agent_id="agent", personas=[], loop_id="loop")
            == []
        )
        assert store.list_stm_entries(agent_id="agent", personas=[], limit=1) == []


def test_raw_memory_store_embed_status_error(tmp_path: Path) -> None:
    """Handles embed status updates after close."""
    db_path = tmp_path / "raw.sqlite"
    store = RawMemoryStore(db_path)
    store.close()
    store.update_ltm_embed_status("ltm", "embedded")
