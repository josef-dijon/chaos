import chromadb
import uuid
from typing import List, Optional, Dict, Any
from agent_of_chaos.config import Config
from agent_of_chaos.infra.utils import logger


class KnowledgeLibrary:
    """
    Manages the static knowledge base using ChromaDB.
    """

    def __init__(self, config: Config, collection_name: str = "knowledge_base"):
        """
        Initializes the knowledge library backed by ChromaDB.

        Args:
            config: Application configuration providing the storage path.
            collection_name: The Chroma collection name to use.
        """
        self.chroma_client = chromadb.PersistentClient(
            path=str(config.get_chroma_db_path())
        )
        self.collection = self.chroma_client.get_or_create_collection(
            name=collection_name
        )

    def add_document(
        self, content: str, domain: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Adds a document to the knowledge base.

        Args:
            content: The document text to store.
            domain: The domain label for access control.
            metadata: Optional metadata to attach.
        """
        if metadata is None:
            metadata = {}

        metadata["domain"] = domain

        try:
            self.collection.add(
                documents=[content], metadatas=[metadata], ids=[str(uuid.uuid4())]
            )
        except Exception as e:
            logger.error(f"Failed to add to KnowledgeLibrary: {e}")

    def search(
        self,
        query: str,
        n_results: int = 3,
        whitelist: Optional[List[str]] = None,
        blacklist: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Searches for knowledge, adhering to access control.

        Args:
            query: The search query string.
            n_results: Maximum number of documents to return.
            whitelist: Allowed domain list.
            blacklist: Forbidden domain list.

        Returns:
            A list of matching document strings.
        """
        where_filter = {}

        # Access Control Logic
        if whitelist is not None:
            where_filter["domain"] = {"$in": whitelist}
        elif blacklist is not None:
            where_filter["domain"] = {"$nin": blacklist}

        # If where_filter is empty, pass None to avoid Chroma error if strictly typed?
        # Chroma expects None if no filter.
        final_where = where_filter if where_filter else None

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=final_where,  # type: ignore
            )

            if results and results["documents"]:
                return results["documents"][0]
            return []
        except Exception as e:
            logger.error(f"Failed to search KnowledgeLibrary: {e}")
            return []
