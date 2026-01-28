from enum import Enum, auto


class BlockState(Enum):
    """Execution state of a block."""

    READY = auto()
    BUSY = auto()
    WAITING = auto()
