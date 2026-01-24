"""Abstract memory view interface."""

from abc import ABC, abstractmethod
from typing import List


class MemoryView(ABC):
    """
    Defines the interface for persona-scoped memory access.
    """

    @abstractmethod
    def retrieve(self, query: str, n_results: int = 5) -> List[str]:
        """
        Retrieves LTM snippets for the given query.

        Args:
            query: The query string.
            n_results: Maximum results to return.

        Returns:
            A list of memory snippets.
        """
        raise NotImplementedError

    @abstractmethod
    def get_recent_stm_as_string(self, limit: int = 1) -> str:
        """
        Returns recent STM summaries for the scoped personas.

        Args:
            limit: Maximum number of summaries to return.

        Returns:
            A formatted STM summary string.
        """
        raise NotImplementedError
