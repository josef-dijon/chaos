import chromadb
from typing import List, Dict, Any, Deque, Optional
from collections import deque
import uuid
import time
from agent_of_chaos.config import settings
from agent_of_chaos.infra.utils import logger


class MemoryContainer:
    """
    Manages Long-Term (ChromaDB) and Short-Term (Deque) memory.
    """

    def __init__(self, collection_name: str = "agent_memories"):
        self.chroma_client = chromadb.PersistentClient(
            path=str(settings.get_chroma_db_path())
        )
        self.collection = self.chroma_client.get_or_create_collection(
            name=collection_name
        )
        self.stm: Deque[Dict[str, Any]] = deque(maxlen=20)  # Context window buffer

    def record(
        self,
        role: str,
        content: str,
        thinking_tokens: str = "",
        importance: float = 0.5,
    ) -> None:
        """
        Records an interaction to both STM and LTM.
        """
        timestamp = time.time()

        # Add to STM
        memory_item = {
            "role": role,
            "content": content,
            "thinking_tokens": thinking_tokens,
            "importance": importance,
            "timestamp": timestamp,
        }
        self.stm.append(memory_item)

        # Add to LTM
        try:
            self.collection.add(
                documents=[content],
                metadatas=[
                    {
                        "role": role,
                        "thinking": thinking_tokens,
                        "importance": importance,
                        "timestamp": timestamp,
                    }
                ],
                ids=[str(uuid.uuid4())],
            )
        except Exception as e:
            logger.error(f"Failed to save to LTM: {e}")

    def retrieve(
        self, query: str, n_results: int = 5, min_importance: float = 0.0
    ) -> List[str]:
        """
        Retrieves relevant memories from LTM, filtering by importance.
        """
        try:
            where_filter = (
                {"importance": {"$gte": min_importance}} if min_importance > 0 else None
            )

            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter,  # type: ignore
            )

            if results and results["documents"]:
                return results["documents"][0]
            return []
        except Exception as e:
            logger.error(f"Failed to retrieve from LTM: {e}")
            return []

    def get_stm_as_string(self) -> str:
        """
        Returns the Short-Term Memory formatted as a conversation string.
        """
        buffer = []
        for item in self.stm:
            buffer.append(f"{item['role']}: {item['content']}")
        return "\n".join(buffer)
