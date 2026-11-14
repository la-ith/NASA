"""Season totals and indicators I1-I6 (section 17). Plain Python, no data libraries."""
import math
import statistics
from dataclasses import dataclass
from datetime import date, timedelta

from app.services.validation import DailyRecord

BASELINE_YEARS = range(1991, 2021)  # seasons 1991/92 to 2020/21
MIN_SEASON_COVERAGE = 0.95
MIN_BASELINE_SEASONS = 24
RECENT_SEASON_COUNT = 5
MIN_RECENT_SEASONS = 4


def season_label(start_year: int) -> str:
    return f"{start_year}/{(start_year + 1) % 100:02d}"


@dataclass(frozen=True)
class SeasonTotal:  # I1
    start_year: int
    label: str
    days: int
    valid_days: int
    total_mm: float | None  # None: under 95% coverage, so the season is unavailable


def seasonal_totals(record: DailyRecord, first_year: int, last_year: int) -> list[SeasonTotal]:
    seasons = []
    for year in range(first_year, last_year + 1):
        start, end = date(year, 10, 1), date(year + 1, 5, 31)
        days = (end - start).days + 1  # 243, or 244 when February has 29 days
        daily = (record.values.get(start + timedelta(days=i)) for i in range(days))
        valid = [v for v in daily if v is not None]
        enough = len(valid) >= math.ceil(MIN_SEASON_COVERAGE * days)
        seasons.append(SeasonTotal(year, season_label(year), days, len(valid), sum(valid) if enough else None))
    return seasons


@dataclass(frozen=True)
class Indicators:
    baseline_totals_mm: list[float]  # valid baseline seasons; used by I5 and R4
    baseline_mean_mm: float | None  # I2
    baseline_sd_mm: float | None
    baseline_cv_pct: float | None  # I4
    anomalies_pct: dict[str, float | None]  # I3, one per recent season
    recent_shift_pct: float | None  # I6, context only


def compute_indicators(seasons: list[SeasonTotal], candidate_year: int) -> Indicators:
    by_year = {s.start_year: s for s in seasons}
    baseline = [by_year[y].total_mm for y in BASELINE_YEARS if by_year[y].total_mm is not None]
    recent_years = range(candidate_year - RECENT_SEASON_COUNT, candidate_year)
    mean = statistics.fmean(baseline) if len(baseline) >= MIN_BASELINE_SEASONS else None
    if not mean:  # too few valid seasons (or no rain at all): baseline unavailable
        return Indicators(baseline, None, None, None, {season_label(y): None for y in recent_years}, None)

    sd = statistics.stdev(baseline)  # sample standard deviation, n - 1
    anomalies: dict[str, float | None] = {}
    recent: list[float] = []
    for year in recent_years:
        total = by_year[year].total_mm
        anomalies[season_label(year)] = None if total is None else (total - mean) / mean * 100
        if total is not None:
            recent.append(total)
    shift = (statistics.fmean(recent) - mean) / mean * 100 if len(recent) >= MIN_RECENT_SEASONS else None
    return Indicators(baseline, mean, sd, sd / mean * 100, anomalies, shift)


def seasons_meeting(indicators: Indicators, threshold_mm: float) -> tuple[int, int]:
    """I5: (n, N), the number of valid baseline seasons with a total >= threshold. Needs I2."""
    totals = indicators.baseline_totals_mm
    return sum(t >= threshold_mm for t in totals), len(totals)
