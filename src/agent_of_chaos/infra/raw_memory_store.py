"""Raw memory storage backed by SQLite."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from uuid import uuid4

from agent_of_chaos.domain.memory_event_kind import MemoryEventKind
from agent_of_chaos.infra.utils import logger

RAW_SCHEMA_VERSION = "1"


@dataclass(frozen=True)
class IdeticEvent:
    """
    Represents an idetic memory event.
    """

    id: str
    ts: str
    agent_id: str
    persona: str
    loop_id: str
    kind: MemoryEventKind | str
    visibility: str
    content: str
    metadata: Dict[str, Any]


class RawMemoryStore:
    """
    SQLite-backed store for raw memory events and summaries.
    """

    def __init__(self, db_path: Path) -> None:
        """
        Initializes a new raw memory store backed by SQLite.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self._initialize_schema()

    def close(self) -> None:
        """
        Closes the underlying SQLite connection.
        """
        self.connection.close()

    def __enter__(self) -> "RawMemoryStore":
        """
        Enters a context manager for the raw store.

        Returns:
            The raw memory store instance.
        """
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        """
        Exits the context manager and closes the connection.

        Args:
            exc_type: The exception type, if any.
            exc: The exception instance, if any.
            traceback: The traceback, if any.
        """
        self.close()

    def _initialize_schema(self) -> None:
        """
        Ensures required tables exist with the expected schema.
        """
        with self.connection:
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_meta (
                  key TEXT PRIMARY KEY,
                  value TEXT NOT NULL
                )
                """
            )
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS idetic_events (
                  id TEXT PRIMARY KEY,
                  ts TEXT NOT NULL,
                  agent_id TEXT NOT NULL,
                  persona TEXT NOT NULL,
                  loop_id TEXT NOT NULL,
                  kind TEXT NOT NULL,
                  visibility TEXT NOT NULL,
                  content TEXT NOT NULL,
                  metadata_json TEXT NOT NULL DEFAULT '{}'
                )
                """
            )
            self.connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_idetic_agent_persona_ts
                  ON idetic_events(agent_id, persona, ts)
                """
            )
            self.connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_idetic_agent_persona_loop
                  ON idetic_events(agent_id, persona, loop_id)
                """
            )
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ltm_entries (
                  id TEXT PRIMARY KEY,
                  idetic_id TEXT NOT NULL UNIQUE,
                  ts TEXT NOT NULL,
                  agent_id TEXT NOT NULL,
                  persona TEXT NOT NULL,
                  loop_id TEXT NOT NULL,
                  kind TEXT NOT NULL,
                  visibility TEXT NOT NULL,
                  summary TEXT NOT NULL,
                  importance REAL NOT NULL DEFAULT 0.0,
                  embed_status TEXT NOT NULL DEFAULT 'pending',
                  metadata_json TEXT NOT NULL DEFAULT '{}'
                )
                """
            )
            self.connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ltm_agent_persona_ts
                  ON ltm_entries(agent_id, persona, ts)
                """
            )
            self.connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ltm_agent_persona_loop
                  ON ltm_entries(agent_id, persona, loop_id)
                """
            )
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS stm_entries (
                  id TEXT PRIMARY KEY,
                  ts_start TEXT NOT NULL,
                  ts_end TEXT NOT NULL,
                  agent_id TEXT NOT NULL,
                  persona TEXT NOT NULL,
                  loop_id TEXT NOT NULL,
                  summary TEXT NOT NULL,
                  metadata_json TEXT NOT NULL DEFAULT '{}',
                  UNIQUE(agent_id, persona, loop_id)
                )
                """
            )
            self.connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_stm_agent_persona_ts_end
                  ON stm_entries(agent_id, persona, ts_end)
                """
            )
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS stm_ltm_map (
                  stm_id TEXT NOT NULL,
                  ltm_id TEXT NOT NULL,
                  seq INTEGER NOT NULL,
                  PRIMARY KEY (stm_id, ltm_id)
                )
                """
            )
            self.connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_stm_ltm_stm_seq
                  ON stm_ltm_map(stm_id, seq)
                """
            )

        self._ensure_schema_version()

    def _ensure_schema_version(self) -> None:
        """
        Ensures the schema version metadata is set.
        """
        current = self.connection.execute(
            "SELECT value FROM schema_meta WHERE key = ?", ("schema_version",)
        ).fetchone()
        if current:
            return

        with self.connection:
            self.connection.execute(
                "INSERT INTO schema_meta (key, value) VALUES (?, ?)",
                ("schema_version", RAW_SCHEMA_VERSION),
            )

    def record_event(
        self,
        agent_id: str,
        persona: str,
        loop_id: str,
        kind: MemoryEventKind | str,
        visibility: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 0.0,
        summary: Optional[str] = None,
    ) -> tuple[str, str, str]:
        """
        Records an idetic event and its LTM mirror entry.

        Args:
            agent_id: The owning agent identifier.
            persona: The persona emitting the event.
            loop_id: The loop identifier.
            kind: The event kind.
            visibility: Visibility category.
            content: Raw event content.
            metadata: Additional metadata payload.
            importance: Importance score for the LTM entry.
            summary: Optional summary for the LTM entry.

        Returns:
            The idetic event id, LTM id, and timestamp.
        """
        event_id = str(uuid4())
        ltm_id = str(uuid4())
        ts = datetime.now(timezone.utc).isoformat()
        if not isinstance(kind, MemoryEventKind):
            try:
                kind = MemoryEventKind(kind)
            except ValueError:
                logger.warning(f"Unknown event kind recorded: {kind}")
                kind = MemoryEventKind.USER_INPUT
        kind_value = kind.value
        metadata_json = json.dumps(metadata or {})
        ltm_summary = summary or content

        with self.connection:
            self.connection.execute(
                """
                INSERT INTO idetic_events (
                  id, ts, agent_id, persona, loop_id, kind, visibility, content, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    ts,
                    agent_id,
                    persona,
                    loop_id,
                    kind_value,
                    visibility,
                    content,
                    metadata_json,
                ),
            )
            self.connection.execute(
                """
                INSERT INTO ltm_entries (
                  id, idetic_id, ts, agent_id, persona, loop_id, kind, visibility,
                  summary, importance, embed_status, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ltm_id,
                    event_id,
                    ts,
                    agent_id,
                    persona,
                    loop_id,
                    kind_value,
                    visibility,
                    ltm_summary,
                    importance,
                    "pending",
                    metadata_json,
                ),
            )
        return event_id, ltm_id, ts

    def update_ltm_embed_status(self, ltm_id: str, status: str) -> None:
        """
        Updates the embedding status for an LTM entry.

        Args:
            ltm_id: The LTM entry identifier.
            status: The new embedding status.
        """
        try:
            with self.connection:
                self.connection.execute(
                    "UPDATE ltm_entries SET embed_status = ? WHERE id = ?",
                    (status, ltm_id),
                )
        except sqlite3.Error as exc:
            logger.error(f"Failed to update LTM embed status: {exc}")

    def list_idetic_events(
        self, agent_id: str, personas: Iterable[str], loop_id: str
    ) -> List[IdeticEvent]:
        """
        Lists idetic events for a loop and persona set.

        Args:
            agent_id: The agent identifier.
            personas: Persona values to include.
            loop_id: The loop identifier.

        Returns:
            A list of idetic events ordered by timestamp.
        """
        persona_list = list(personas)
        if not persona_list:
            return []
        placeholders = ",".join(["?"] * len(persona_list))
        query = (
            "SELECT id, ts, agent_id, persona, loop_id, kind, visibility, content, metadata_json "
            "FROM idetic_events WHERE agent_id = ? AND loop_id = ? "
            f"AND persona IN ({placeholders}) ORDER BY ts"
        )
        rows = self.connection.execute(
            query, (agent_id, loop_id, *persona_list)
        ).fetchall()
        events: List[IdeticEvent] = []
        for row in rows:
            events.append(
                IdeticEvent(
                    id=row["id"],
                    ts=row["ts"],
                    agent_id=row["agent_id"],
                    persona=row["persona"],
                    loop_id=row["loop_id"],
                    kind=row["kind"],
                    visibility=row["visibility"],
                    content=row["content"],
                    metadata=json.loads(row["metadata_json"] or "{}"),
                )
            )
        return events

    def list_ltm_ids(self, agent_id: str, persona: str, loop_id: str) -> List[str]:
        """
        Lists LTM ids for a loop and persona.

        Args:
            agent_id: The agent identifier.
            persona: The persona name.
            loop_id: The loop identifier.

        Returns:
            Ordered LTM entry identifiers.
        """
        rows = self.connection.execute(
            """
            SELECT id FROM ltm_entries
            WHERE agent_id = ? AND persona = ? AND loop_id = ?
            ORDER BY ts
            """,
            (agent_id, persona, loop_id),
        ).fetchall()
        return [row["id"] for row in rows]

    def create_stm_entry(
        self,
        agent_id: str,
        persona: str,
        loop_id: str,
        summary: str,
        ts_start: str,
        ts_end: str,
        ltm_ids: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Creates or replaces an STM summary entry and its LTM mapping.

        Args:
            agent_id: The agent identifier.
            persona: The persona name.
            loop_id: The loop identifier.
            summary: The summary text.
            ts_start: Loop start timestamp.
            ts_end: Loop end timestamp.
            ltm_ids: Ordered LTM ids for the loop.
            metadata: Additional metadata payload.

        Returns:
            The STM entry id.
        """
        metadata_json = json.dumps(metadata or {})
        with self.connection:
            existing = self.connection.execute(
                """
                SELECT id FROM stm_entries
                WHERE agent_id = ? AND persona = ? AND loop_id = ?
                """,
                (agent_id, persona, loop_id),
            ).fetchone()

            if existing:
                stm_id = existing["id"]
                self.connection.execute(
                    "DELETE FROM stm_ltm_map WHERE stm_id = ?", (stm_id,)
                )
                self.connection.execute(
                    "DELETE FROM stm_entries WHERE id = ?", (stm_id,)
                )
            else:
                stm_id = str(uuid4())

            self.connection.execute(
                """
                INSERT INTO stm_entries (
                  id, ts_start, ts_end, agent_id, persona, loop_id, summary, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    stm_id,
                    ts_start,
                    ts_end,
                    agent_id,
                    persona,
                    loop_id,
                    summary,
                    metadata_json,
                ),
            )
            for seq, ltm_id in enumerate(ltm_ids):
                self.connection.execute(
                    """
                    INSERT INTO stm_ltm_map (stm_id, ltm_id, seq)
                    VALUES (?, ?, ?)
                    """,
                    (stm_id, ltm_id, seq),
                )
        return stm_id

    def list_stm_entries(
        self, agent_id: str, personas: Iterable[str], limit: int
    ) -> List[Dict[str, Any]]:
        """
        Lists STM summaries for the given personas.

        Args:
            agent_id: The agent identifier.
            personas: Persona values to include.
            limit: Maximum number of entries to return.

        Returns:
            List of STM summary rows.
        """
        persona_list = list(personas)
        if not persona_list:
            return []
        placeholders = ",".join(["?"] * len(persona_list))
        query = (
            "SELECT id, ts_start, ts_end, agent_id, persona, loop_id, summary, metadata_json "
            "FROM stm_entries WHERE agent_id = ? "
            f"AND persona IN ({placeholders}) ORDER BY ts_end DESC LIMIT ?"
        )
        rows = self.connection.execute(
            query, (agent_id, *persona_list, limit)
        ).fetchall()
        results: List[Dict[str, Any]] = []
        for row in rows:
            results.append(
                {
                    "id": row["id"],
                    "ts_start": row["ts_start"],
                    "ts_end": row["ts_end"],
                    "agent_id": row["agent_id"],
                    "persona": row["persona"],
                    "loop_id": row["loop_id"],
                    "summary": row["summary"],
                    "metadata": json.loads(row["metadata_json"] or "{}"),
                }
            )
        return results
