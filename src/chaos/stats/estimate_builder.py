from typing import Iterable, List

from chaos.domain.block_estimate import BlockEstimate
from chaos.domain.messages import Request
from chaos.stats.block_attempt_record import BlockAttemptRecord
from chaos.stats.block_stats_identity import BlockStatsIdentity
from chaos.stats.statistics import confidence_from_sample_size, mean_std


def build_estimate_from_records(
    identity: BlockStatsIdentity,
    request: Request,
    records: Iterable[BlockAttemptRecord],
    prior: BlockEstimate,
) -> BlockEstimate:
    """Build a BlockEstimate from recorded attempts.

    Args:
        identity: Stable block identity metadata.
        request: Request to estimate.
        records: Attempt records for the block.
        prior: Prior estimate used when data is missing.

    Returns:
        A BlockEstimate built from records with fallbacks to priors.
    """

    del request
    record_list: List[BlockAttemptRecord] = list(records)
    sample_size = len(record_list)
    if sample_size == 0:
        return prior

    time_values = [record.duration_ms for record in record_list]
    cost_values = [
        record.cost_usd for record in record_list if record.cost_usd is not None
    ]
    llm_call_values = [
        record.llm_calls for record in record_list if record.llm_calls is not None
    ]
    block_exec_values = [
        record.block_executions
        for record in record_list
        if record.block_executions is not None
    ]

    time_mean, time_std = mean_std(time_values)
    cost_mean, cost_std = mean_std(cost_values)
    llm_calls_mean, _ = mean_std(llm_call_values)
    block_exec_mean, _ = mean_std(block_exec_values)

    notes = list(prior.notes)
    if not cost_values:
        notes.append("cost_estimate_fell_back_to_prior")
    if not llm_call_values:
        notes.append("llm_calls_estimate_fell_back_to_prior")
    if not block_exec_values:
        notes.append("block_exec_estimate_fell_back_to_prior")

    return BlockEstimate(
        block_name=identity.block_name,
        block_type=identity.block_type,
        version=identity.version,
        estimate_source="stats",
        confidence=confidence_from_sample_size(sample_size),
        sample_size=sample_size,
        time_ms_mean=time_mean,
        time_ms_std=time_std,
        cost_usd_mean=cost_mean if cost_values else prior.cost_usd_mean,
        cost_usd_std=cost_std if cost_values else prior.cost_usd_std,
        expected_llm_calls=llm_calls_mean
        if llm_call_values
        else prior.expected_llm_calls,
        expected_block_executions=block_exec_mean
        if block_exec_values
        else prior.expected_block_executions,
        notes=notes,
    )
