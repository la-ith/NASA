"""Does the grid cell represent the field? (section 16.1)"""
import statistics
from dataclasses import dataclass
from typing import Literal

from app.services.indicators import SeasonTotal

REPRESENTATIVE_RATIO = (0.80, 1.25)  # team choice, shown on the evidence screen


@dataclass(frozen=True)
class StationReference:
    name: str
    source: str
    mean_oct_may_mm: float
    first_year: int  # first season's start year: 2007 means 2007/08
    last_year: int


@dataclass(frozen=True)
class SiteCheck:
    result: Literal["representative", "not_representative", "not_checked"]
    reason: str
    cell_mean_mm: float | None = None
    station_mean_mm: float | None = None
    ratio: float | None = None
    station_name: str | None = None


def run_site_check(seasons: list[SeasonTotal], station: StationReference | None) -> SiteCheck:
    if station is None:
        return SiteCheck("not_checked", "absolute rainfall not checked against a local record")
    window = [s for s in seasons if station.first_year <= s.start_year <= station.last_year]
    expected = station.last_year - station.first_year + 1
    if len(window) != expected or any(s.total_mm is None for s in window):
        return SiteCheck("not_checked", "the grid record does not fully cover the station period")
    cell = statistics.fmean(s.total_mm for s in window)
    ratio = cell / station.mean_oct_may_mm
    low, high = REPRESENTATIVE_RATIO
    if low <= ratio <= high:
        return SiteCheck("representative", "grid cell matches the station record", cell, station.mean_oct_may_mm,
                         ratio, station.name)
    reason = f"the grid cell has {ratio:.0%} of the rainfall recorded at {station.name} station"
    return SiteCheck("not_representative", reason, cell, station.mean_oct_may_mm, ratio, station.name)
