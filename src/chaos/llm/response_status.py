from enum import Enum


class ResponseStatus(str, Enum):
    """Internal status for LLM layer responses."""

    SUCCESS = "success"
    SEMANTIC_ERROR = "semantic_error"
    MECHANICAL_ERROR = "mechanical_error"
    CAPACITY_ERROR = "capacity_error"
    CONFIG_ERROR = "config_error"
    BUDGET_ERROR = "budget_error"
