from chaos.domain.block import Block
from chaos.domain.block_estimate import BlockEstimate
from chaos.domain.messages import Request, Response
from chaos.stats.block_attempt_record import BlockAttemptRecord
from chaos.stats.block_stats_identity import BlockStatsIdentity
from chaos.stats.json_block_stats_store import JsonBlockStatsStore
from chaos.stats.statistics import confidence_from_sample_size, mean_std
from chaos.stats.in_memory_block_stats_store import InMemoryBlockStatsStore
from chaos.stats.store_registry import set_default_store


class EstimateBlock(Block):
    """Simple block used for estimation tests."""

    def build(self) -> None:
        """No graph for the estimate test block."""

    def _execute_primitive(self, request: Request) -> Response:
        """Return the payload for testing purposes."""

        return Response(success=True, data=request.payload)


def test_store_returns_prior_when_empty() -> None:
    """Ensure the in-memory store returns a prior estimate on cold start."""

    store = InMemoryBlockStatsStore()
    identity = BlockStatsIdentity(block_name="block", block_type="test", version=None)
    estimate = store.estimate(identity, Request())

    assert isinstance(estimate, BlockEstimate)
    assert estimate.estimate_source == "prior"
    assert estimate.sample_size == 0


def test_store_estimate_from_records() -> None:
    """Ensure the store builds estimates from recorded attempts."""

    store = InMemoryBlockStatsStore()
    identity = BlockStatsIdentity(block_name="block", block_type="test", version=None)
    record = BlockAttemptRecord(
        trace_id="trace",
        run_id="run",
        span_id="span",
        parent_span_id=None,
        block_name="block",
        block_type="test",
        version=None,
        node_name=None,
        attempt=1,
        success=True,
        reason=None,
        error_type=None,
        duration_ms=123.0,
        cost_usd=0.25,
        model=None,
        input_tokens=10,
        output_tokens=20,
        llm_calls=0,
        block_executions=1,
    )
    store.record_attempt(record)
    estimate = store.estimate(identity, Request())

    assert estimate.estimate_source == "stats"
    assert estimate.sample_size == 1
    assert estimate.time_ms_mean == 123.0
    assert estimate.cost_usd_mean == 0.25
    assert estimate.expected_block_executions == 1.0


def test_block_execute_records_attempt() -> None:
    """Ensure block execution records attempts into the default store."""

    store = InMemoryBlockStatsStore()
    set_default_store(store)
    block = EstimateBlock(name="block")

    block.execute(Request(payload={"value": 1}))
    estimate = block.estimate_execution(Request(payload={"value": 1}))

    assert estimate.estimate_source == "stats"
    assert estimate.sample_size == 1


def test_mean_std_empty() -> None:
    """Ensure mean/std returns zeros for empty inputs."""

    mean_value, std_value = mean_std([])

    assert mean_value == 0.0
    assert std_value == 0.0


def test_mean_std_values() -> None:
    """Ensure mean/std returns expected values."""

    mean_value, std_value = mean_std([2.0, 4.0])

    assert mean_value == 3.0
    assert std_value == 1.0


def test_confidence_from_sample_size() -> None:
    """Ensure confidence mapping aligns with thresholds."""

    assert confidence_from_sample_size(0) == "low"
    assert confidence_from_sample_size(5) == "medium"
    assert confidence_from_sample_size(20) == "high"


def test_json_store_roundtrip(tmp_path) -> None:
    """Ensure JSON store persists and reloads attempts."""

    path = tmp_path / "stats.json"
    store = JsonBlockStatsStore(path)
    identity = BlockStatsIdentity(block_name="block", block_type="test", version=None)
    record = BlockAttemptRecord(
        trace_id="trace",
        run_id="run",
        span_id="span",
        parent_span_id=None,
        block_name="block",
        block_type="test",
        version=None,
        node_name=None,
        attempt=1,
        success=True,
        reason=None,
        error_type=None,
        duration_ms=50.0,
        cost_usd=0.1,
        model="model",
        input_tokens=5,
        output_tokens=10,
        llm_calls=1,
        block_executions=1,
    )
    store.record_attempt(record)

    reloaded = JsonBlockStatsStore(path)
    estimate = reloaded.estimate(identity, Request())

    assert estimate.sample_size == 1
    assert estimate.estimate_source == "stats"
    assert estimate.expected_block_executions == 1.0
