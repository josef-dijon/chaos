"""Actor-scoped memory view."""

from typing import List, TYPE_CHECKING

from agent_of_chaos.infra.memory_view import MemoryView

if TYPE_CHECKING:
    from agent_of_chaos.infra.memory_container import MemoryContainer


class ActorMemoryView(MemoryView):
    """
    Provides actor-only access to memory layers.
    """

    def __init__(self, container: "MemoryContainer") -> None:
        self.container = container

    def retrieve(self, query: str, n_results: int = 5) -> List[str]:
        """
        Retrieves actor memories.

        Args:
            query: The query string.
            n_results: Maximum results to return.

        Returns:
            A list of memory snippets.
        """
        return self.container.retrieve_for_personas(["actor"], query, n_results)

    def get_recent_stm_as_string(self, limit: int = 1) -> str:
        """
        Returns recent actor STM summaries.

        Args:
            limit: Maximum number of summaries to return.

        Returns:
            A formatted STM summary string.
        """
        return self.container.get_recent_stm_as_string(["actor"], limit)
