"""Crop water demand and root-zone water capacity (FAO-56 chapters 6 and 8, single crop coefficient)."""
from dataclasses import dataclass

from app.science.fao56 import saturation_vapour_pressure

U2_LIMITS = (1.0, 6.0)  # validity range of Eq. 62 for mean u2 [m s-1]
RHMIN_LIMITS = (20.0, 80.0)  # validity range of Eq. 62 for mean RHmin [%]


@dataclass(frozen=True)
class Stages:
    """FAO-56 Table 11 stage lengths [days]: initial, crop development, mid-season, late season."""
    initial: int
    development: int
    mid: int
    late: int

    @property
    def total(self) -> int:
        return self.initial + self.development + self.mid + self.late


def kc_curve(stages: Stages, kc_ini: float, kc_mid: float, kc_end: float) -> list[float]:
    """Daily Kc for days 1..L of the season (FAO-56 Fig. 25 and Eq. 66).

    Kc is constant at Kc ini through the initial stage, rises linearly to Kc mid across development,
    stays at Kc mid through mid-season, and falls linearly to Kc end on the last day of the late season.
    """
    curve = [kc_ini] * stages.initial
    curve += [kc_ini + k / stages.development * (kc_mid - kc_ini) for k in range(1, stages.development + 1)]
    curve += [kc_mid] * stages.mid
    curve += [kc_mid + k / stages.late * (kc_end - kc_mid) for k in range(1, stages.late + 1)]
    return curve


def min_relative_humidity(t_dew_c: float, t_max_c: float) -> float:
    """Eq. 63: RHmin = 100 e°(Tdew) / e°(Tmax) [%], the daily minimum humidity estimated from dewpoint."""
    return 100.0 * saturation_vapour_pressure(t_dew_c) / saturation_vapour_pressure(t_max_c)


@dataclass(frozen=True)
class ClimateAdjustment:
    kc: float
    u2_used: float
    rhmin_used: float
    limited: bool  # True when u2 or RHmin was outside the Eq. 62 range and was limited to it


def adjust_kc_for_climate(kc_table: float, u2_mean: float, rhmin_mean: float, height_m: float) -> ClimateAdjustment:
    """Eq. 62 (Kc mid) and Eq. 65 (Kc end): Kc = Kc(Tab) + [0.04 (u2 - 2) - 0.004 (RHmin - 45)] (h/3)^0.3.

    FAO-56 gives the equation for 1 ≤ u2 ≤ 6 m s-1 and 20 ≤ RHmin ≤ 80 %; values outside are limited to the
    range and the result says so. Callers apply it to Kc end only when Kc end(Tab) ≥ 0.45 (FAO-56, Eq. 65).
    """
    u2 = min(max(u2_mean, U2_LIMITS[0]), U2_LIMITS[1])
    rhmin = min(max(rhmin_mean, RHMIN_LIMITS[0]), RHMIN_LIMITS[1])
    kc = kc_table + (0.04 * (u2 - 2.0) - 0.004 * (rhmin - 45.0)) * (height_m / 3.0) ** 0.3
    return ClimateAdjustment(kc, u2, rhmin, u2 != u2_mean or rhmin != rhmin_mean)


def adjusted_depletion_fraction(p_table: float, etc_mm: float) -> float:
    """FAO-56 Table 22 note: p = p(Table 22) + 0.04 (5 - ETc), limited to 0.1 ≤ p ≤ 0.8."""
    return min(max(p_table + 0.04 * (5.0 - etc_mm), 0.1), 0.8)


def total_available_water(theta_fc: float, theta_wp: float, root_depth_m: float) -> float:
    """Eq. 82 for a homogeneous root zone: TAW = 1000 (θFC - θWP) Zr [mm], θ in m³ m-3."""
    return 1000.0 * (theta_fc - theta_wp) * root_depth_m


@dataclass(frozen=True)
class Horizon:
    top_cm: float
    bottom_cm: float
    awc: float  # available water capacity [cm water per cm soil = m³ m-3], NRCS awc_r


def layered_total_available_water(horizons: list[Horizon], root_depth_m: float) -> float:
    """Eq. 82 integrated over soil layers: TAW = Σ 10 · AWCi · Δzi [mm], Δzi in cm within the root zone.

    Only the part of each horizon above the rooting depth counts. Soil below the deepest horizon
    contributes nothing, so a shallow soil limits TAW instead of being assumed deeper than it is.
    """
    root_cm = root_depth_m * 100.0
    return sum(10.0 * h.awc * max(0.0, min(h.bottom_cm, root_cm) - h.top_cm) for h in horizons)
