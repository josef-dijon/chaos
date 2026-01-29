from math import sqrt
from typing import Iterable, Tuple


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


def confidence_from_sample_size(sample_size: int) -> str:
    """Return a confidence label based on sample size.

    Args:
        sample_size: Number of samples.

    Returns:
        Confidence label string.
    """

    if sample_size >= 20:
        return "high"
    if sample_size >= 5:
        return "medium"
    return "low"
