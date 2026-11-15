"""Summaries of a historical weather-replay ensemble (spec v4.0, section 6).

These describe the spread of simulated outcomes over past seasons. They are not forecast probabilities.
"""
import math
from dataclasses import dataclass


def quantile(values: list[float], q: float) -> float:
    """Linear-interpolation quantile of sorted data (Hyndman and Fan type 7, the NumPy/R default)."""
    data = sorted(values)
    position = (len(data) - 1) * q
    low, high = math.floor(position), math.ceil(position)
    return data[low] + (data[high] - data[low]) * (position - low)


@dataclass(frozen=True)
class Spread:
    n: int
    mean: float
    p10: float
    median: float
    p90: float
    minimum: float
    maximum: float


def spread(values: list[float]) -> Spread | None:
    """None when there are no values; a spread is never invented from an empty ensemble."""
    if not values:
        return None
    return Spread(len(values), sum(values) / len(values), quantile(values, 0.10), quantile(values, 0.50),
                  quantile(values, 0.90), min(values), max(values))
