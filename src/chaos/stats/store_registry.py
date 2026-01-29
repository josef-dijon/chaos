from chaos.config import Config
from chaos.stats.block_stats_store import BlockStatsStore
from chaos.stats.json_block_stats_store import JsonBlockStatsStore

_DEFAULT_STORE: BlockStatsStore = JsonBlockStatsStore(
    Config.load().get_block_stats_path()
)


def get_default_store() -> BlockStatsStore:
    """Return the default block stats store."""

    return _DEFAULT_STORE


def set_default_store(store: BlockStatsStore) -> None:
    """Replace the default block stats store.

    Args:
        store: The new default stats store.
    """

    global _DEFAULT_STORE
    _DEFAULT_STORE = store
