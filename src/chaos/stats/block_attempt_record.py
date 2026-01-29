from typing import Optional

from pydantic import BaseModel, Field


class BlockAttemptRecord(BaseModel):
    """Record of a single block execution attempt for stats tracking."""

    trace_id: str = Field(description="Trace identifier for the run.")
    run_id: str = Field(description="Run identifier for the trace.")
    span_id: str = Field(description="Span identifier for this block attempt.")
    parent_span_id: Optional[str] = Field(
        default=None, description="Parent span identifier, if any."
    )
    block_name: str = Field(description="Stable block instance name.")
    block_type: str = Field(description="Stable block type identifier.")
    version: Optional[str] = Field(default=None, description="Optional block version.")
    node_name: Optional[str] = Field(default=None, description="Composite node name.")
    attempt: int = Field(description="Attempt index for this block execution.")
    success: bool = Field(description="Whether the attempt succeeded.")
    reason: Optional[str] = Field(default=None, description="Failure reason label.")
    error_type: Optional[str] = Field(
        default=None, description="Failure error type classifier."
    )
    duration_ms: float = Field(description="Execution duration in milliseconds.")
    cost_usd: Optional[float] = Field(default=None, description="Actual cost in USD.")
    model: Optional[str] = Field(default=None, description="Model identifier, if any.")
    input_tokens: Optional[int] = Field(
        default=None, description="Input token count, if available."
    )
    output_tokens: Optional[int] = Field(
        default=None, description="Output token count, if available."
    )
    llm_calls: Optional[int] = Field(
        default=None, description="Number of LLM calls made by this attempt."
    )
    block_executions: Optional[int] = Field(
        default=None, description="Number of block executions within this attempt."
    )
