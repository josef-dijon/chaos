from math import sqrt
from typing import Iterable, Tuple

from chaos.domain.block_estimate import EstimateConfidence


def mean_std(values: Iterable[float]) -> Tuple[float, float]:
    """Compute mean and population standard deviation.

    Args:
        values: Iterable of numeric values.

    Returns:
        Tuple containing (mean, std deviation). Returns (0.0, 0.0) if empty.
    """

    collected = list(values)
    if not collected:
        return 0.0, 0.0
    mean_value = sum(collected) / len(collected)
    if len(collected) == 1:
        return mean_value, 0.0
    variance = sum((value - mean_value) ** 2 for value in collected) / len(collected)
    return mean_value, sqrt(variance)


def confidence_from_sample_size(sample_size: int) -> EstimateConfidence:
    """Return a confidence label based on sample size.

    Args:
        sample_size: Number of samples.

    Returns:
        Confidence label.
    """

    if sample_size >= 20:
        return EstimateConfidence.HIGH
    if sample_size >= 5:
        return EstimateConfidence.MEDIUM
    return EstimateConfidence.LOW
