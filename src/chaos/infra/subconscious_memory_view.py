"""Subconscious-scoped memory view."""

from typing import List, TYPE_CHECKING

from chaos.infra.memory_view import MemoryView

if TYPE_CHECKING:
    from chaos.infra.memory_container import MemoryContainer


class SubconsciousMemoryView(MemoryView):
    """
    Provides subconscious access to both actor and subconscious memory layers.
    """

    def __init__(self, container: "MemoryContainer") -> None:
        self.container = container

    def retrieve(self, query: str, n_results: int = 5) -> List[str]:
        """
        Retrieves actor and subconscious memories.

        Args:
            query: The query string.
            n_results: Maximum results per persona.

        Returns:
            A list of memory snippets.
        """
        return self.container.retrieve_for_personas(
            ["actor", "subconscious"], query, n_results
        )

    def get_recent_stm_as_string(self, limit: int = 1) -> str:
        """
        Returns recent STM summaries across personas.

        Args:
            limit: Maximum number of summaries.

        Returns:
            A formatted STM summary string.
        """
        return self.container.get_recent_stm_as_string(["actor", "subconscious"], limit)
