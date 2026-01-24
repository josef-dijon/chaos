"""Memory container orchestrating raw and vector storage."""

from __future__ import annotations

from collections import deque
import json
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional
from uuid import uuid4

import chromadb

from agent_of_chaos.config import Config
from agent_of_chaos.domain import Identity
from agent_of_chaos.domain.memory_event_kind import MemoryEventKind
from agent_of_chaos.infra.raw_memory_store import RawMemoryStore
from agent_of_chaos.infra.utils import logger

if TYPE_CHECKING:
    from agent_of_chaos.infra.actor_memory_view import ActorMemoryView
    from agent_of_chaos.infra.subconscious_memory_view import SubconsciousMemoryView

VISIBILITY_EXTERNAL = "external"
STM_MAX_LINES = 50
EVENT_KINDS = set(MemoryEventKind)


class MemoryContainer:
    """
    Coordinates raw idetic storage, STM summaries, and LTM vector storage.
    """

    def __init__(self, agent_id: str, identity: Identity, config: Config) -> None:
        self.agent_id = agent_id
        self.identity = identity
        self.raw_store = RawMemoryStore(config.get_raw_db_path())
        self.chroma_client = chromadb.PersistentClient(
            path=str(config.get_chroma_db_path())
        )
        self._collections = {
            "actor": self.chroma_client.get_or_create_collection(
                name=self.identity.memory.actor.ltm_collection
            ),
            "subconscious": self.chroma_client.get_or_create_collection(
                name=self.identity.memory.subconscious.ltm_collection
            ),
        }
        self._recent_loop_ids = {
            "actor": deque(maxlen=10),
            "subconscious": deque(maxlen=10),
        }

    def create_loop_id(self) -> str:
        """
        Generates a new loop identifier.

        Returns:
            A unique loop id string.
        """
        return str(uuid4())

    def _normalize_metadata_value(self, value: Any) -> Any:
        """
        Normalizes metadata values for Chroma compatibility.

        Args:
            value: The metadata value to normalize.

        Returns:
            A scalar or serialized string value.
        """
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return json.dumps(value, default=str)

    def record_event(
        self,
        persona: str,
        loop_id: str,
        kind: MemoryEventKind | str,
        visibility: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 0.5,
        summary: Optional[str] = None,
    ) -> Optional[str]:
        """
        Records an idetic event and mirrors it to LTM vector storage.

        Args:
            persona: The persona emitting the event.
            loop_id: The loop identifier.
            kind: The event kind.
            visibility: Visibility category.
            content: The raw event content.
            metadata: Additional metadata payload.
            importance: Importance score for the LTM entry.
            summary: Optional LTM summary.

        Returns:
            The LTM entry id, if created.
        """
        if not isinstance(kind, MemoryEventKind):
            try:
                kind = MemoryEventKind(kind)
            except ValueError:
                logger.warning(f"Unknown event kind recorded: {kind}")
                return None
        if kind not in EVENT_KINDS:
            logger.warning(f"Unknown event kind recorded: {kind}")
        kind_value = kind.value
        try:
            _, ltm_id, ts = self.raw_store.record_event(
                agent_id=self.agent_id,
                persona=persona,
                loop_id=loop_id,
                kind=kind,
                visibility=visibility,
                content=content,
                metadata=metadata,
                importance=importance,
                summary=summary,
            )
        except Exception as exc:
            logger.error(f"Failed to record raw memory event: {exc}")
            return None

        metadata_payload = {
            "agent_id": self.agent_id,
            "persona": persona,
            "kind": kind_value,
            "visibility": visibility,
            "ts": ts,
            "loop_id": loop_id,
            "importance": importance,
        }
        if metadata:
            metadata_payload.update(metadata)
        metadata_payload = {
            key: self._normalize_metadata_value(value)
            for key, value in metadata_payload.items()
        }

        try:
            collection = self._collections[persona]
            collection.upsert(
                documents=[summary or content],
                metadatas=[metadata_payload],
                ids=[ltm_id],
            )
            self.raw_store.update_ltm_embed_status(ltm_id, "embedded")
        except Exception as exc:
            logger.error(f"Failed to save to LTM vector store: {exc}")
            self.raw_store.update_ltm_embed_status(ltm_id, "retry")
        return ltm_id

    def finalize_loop(self, persona: str, loop_id: str) -> None:
        """
        Builds and stores an STM summary for a completed loop.

        Args:
            persona: The persona name.
            loop_id: The loop identifier.
        """
        events = self.raw_store.list_idetic_events(
            agent_id=self.agent_id, personas=[persona], loop_id=loop_id
        )
        if not events:
            return

        ts_start = events[0].ts
        ts_end = events[-1].ts
        summary_lines = []
        for event in events:
            kind_value = (
                event.kind.value
                if isinstance(event.kind, MemoryEventKind)
                else event.kind
            )
            summary_lines.append(f"{kind_value}: {event.content}")
        if len(summary_lines) > STM_MAX_LINES:
            summary_lines = summary_lines[-STM_MAX_LINES:]
        summary = "\n".join(summary_lines)
        ltm_ids = self.raw_store.list_ltm_ids(
            agent_id=self.agent_id, persona=persona, loop_id=loop_id
        )
        self.raw_store.create_stm_entry(
            agent_id=self.agent_id,
            persona=persona,
            loop_id=loop_id,
            summary=summary,
            ts_start=ts_start,
            ts_end=ts_end,
            ltm_ids=ltm_ids,
        )
        self._recent_loop_ids[persona].append(loop_id)

    def retrieve_for_personas(
        self, personas: Iterable[str], query: str, n_results: int = 5
    ) -> List[str]:
        """
        Retrieves vector memories for the given personas.

        Args:
            personas: Persona names to query.
            query: Query string.
            n_results: Max results per persona.

        Returns:
            A list of memory snippets.
        """
        results: List[str] = []
        for persona in personas:
            collection = self._collections.get(persona)
            if not collection:
                continue
            try:
                response = collection.query(
                    query_texts=[query],
                    n_results=n_results,
                    where={
                        "$and": [
                            {"agent_id": {"$eq": self.agent_id}},
                            {"persona": {"$eq": persona}},
                        ]
                    },
                )
                documents = response.get("documents") if response else None
                if documents and documents[0]:
                    results.extend(documents[0])
            except Exception as exc:
                logger.error(f"Failed to retrieve from LTM: {exc}")
        return results

    def get_recent_stm_as_string(self, personas: Iterable[str], limit: int = 1) -> str:
        """
        Returns recent STM summaries as a formatted string.

        Args:
            personas: Persona names to include.
            limit: Maximum number of summaries.

        Returns:
            A formatted STM summary string.
        """
        entries = self.raw_store.list_stm_entries(
            agent_id=self.agent_id, personas=personas, limit=limit
        )
        if not entries:
            return ""
        lines = [
            f"[{entry['persona']}:{entry['loop_id']}] {entry['summary']}"
            for entry in entries
        ]
        return "\n".join(lines)

    def close(self) -> None:
        """
        Closes any underlying storage connections.

        This currently closes the raw SQLite connection and any optional
        Chroma client close hook if available.
        """
        self.raw_store.close()
        close_method = getattr(self.chroma_client, "close", None)
        if callable(close_method):
            close_method()

    def actor_view(self) -> ActorMemoryView:
        """
        Returns a persona-scoped actor memory view.

        Returns:
            The actor memory view.
        """
        from agent_of_chaos.infra.actor_memory_view import ActorMemoryView

        return ActorMemoryView(self)

    def subconscious_view(self) -> SubconsciousMemoryView:
        """
        Returns a persona-scoped subconscious memory view.

        Returns:
            The subconscious memory view.
        """
        from agent_of_chaos.infra.subconscious_memory_view import SubconsciousMemoryView

        return SubconsciousMemoryView(self)
