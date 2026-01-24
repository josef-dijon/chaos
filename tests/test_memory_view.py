"""Tests for the memory view base class."""

import pytest

from agent_of_chaos.infra.memory_view import MemoryView


class DummyView(MemoryView):
    """Concrete implementation that defers to base methods."""

    def retrieve(self, query: str, n_results: int = 5):
        return MemoryView.retrieve(self, query, n_results)

    def get_recent_stm_as_string(self, limit: int = 1) -> str:
        return MemoryView.get_recent_stm_as_string(self, limit)


def test_memory_view_abstract_methods_raise() -> None:
    view = DummyView()

    with pytest.raises(NotImplementedError):
        view.retrieve("query")

    with pytest.raises(NotImplementedError):
        view.get_recent_stm_as_string()
