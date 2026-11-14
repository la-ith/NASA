"""Daily root-zone soil water balance (FAO-56 chapter 8, single crop coefficient, Eqs. 80-88).

Control volume: the root zone of fixed depth Zr. In depletion form (Eq. 85), with Dr = TAW - S:

    Dr,i = Dr,i-1 - (P - RO)i - Ii - CRi + ETa,i + DPi
    DPi  = max((P - RO)i + Ii - ETa,i - Dr,i-1, 0)          (Eq. 88)
    ETa  = Ks Kc ET0                                        (Eq. 80)
    Ks   = (TAW - Dr) / ((1 - p) TAW) if Dr > RAW, else 1   (Eq. 84)

Rain and irrigation arrive early in the day, so Ks uses the depletion after they enter (FAO-56 Example 36).
Runoff RO uses the USDA SCS curve number method. Stated assumptions, also reported with every result:
- capillary rise CR = 0 (water table well below the root zone);
- rooting depth is constant at its maximum from planting (FAO-56 notes this overstates early-season TAW);
- the curve number is for average antecedent moisture (AMC II), not adjusted day by day.
ETa is also limited to the water actually stored (TAW - Dr), so storage can never go negative.
Mass conservation is checked for every run: ΣP - ΣRO + ΣI - ΣETa - ΣDP = ΔS.
"""
import math
from dataclasses import dataclass, field

from app.science.crop import adjusted_depletion_fraction


def scs_runoff(precip_mm: float, curve_number: float) -> float:
    """USDA SCS curve number runoff (TR-55): S = 25400/CN - 254, Ia = 0.2 S, Q = (P - Ia)² / (P - Ia + S) [mm]."""
    retention = 25400.0 / curve_number - 254.0
    initial_abstraction = 0.2 * retention
    if precip_mm <= initial_abstraction:
        return 0.0
    return (precip_mm - initial_abstraction) ** 2 / (precip_mm - initial_abstraction + retention)


def water_stress_coefficient(depletion: float, taw: float, p: float) -> float:
    """Eq. 84: Ks = (TAW - Dr) / ((1 - p) TAW) when Dr > RAW = p TAW, otherwise 1."""
    raw = p * taw
    if depletion <= raw:
        return 1.0
    return max(0.0, (taw - depletion) / ((1.0 - p) * taw))


@dataclass
class BalanceResult:
    precipitation: float = 0.0
    runoff: float = 0.0
    irrigation_net: float = 0.0
    etc_standard: float = 0.0  # Σ Kc ET0, demand without water stress (Eq. 58)
    eta: float = 0.0  # Σ Ks Kc ET0, simulated actual ET (Eq. 80)
    drainage: float = 0.0
    stress_days: int = 0  # days with Ks < 1
    irrigation_events: int = 0
    initial_depletion: float = 0.0
    final_depletion: float = 0.0
    closure_residual: float = 0.0  # mm; must be ~0 (floating-point only)
    daily_ks: list[float] = field(default_factory=list)
    daily_depletion: list[float] = field(default_factory=list)

    @property
    def deficit(self) -> float:
        """ETc standard - ETa: demand the root zone could not supply [mm]."""
        return self.etc_standard - self.eta


def simulate(et0: list[float], kc: list[float], precip: list[float], taw: float, p_table: float,
             curve_number: float, initial_depletion: float, irrigate: bool = False,
             adjust_p: bool = True) -> BalanceResult:
    """Run the daily balance over one season. All lists are aligned day by day [mm day-1, Kc dimensionless].

    irrigate=False is the rain-fed scenario: missing water stays a simulated deficit.
    irrigate=True refills the root zone to field capacity (net irrigation) whenever depletion reaches RAW,
    the FAO-56 "irrigate when RAW is depleted" rule. Irrigation is net: application losses are not modelled here.
    """
    if not (len(et0) == len(kc) == len(precip)):
        raise ValueError("et0, kc and precip must cover the same days")
    if not 0.0 <= initial_depletion <= taw:
        raise ValueError("initial depletion must be between 0 and TAW")
    r = BalanceResult(initial_depletion=initial_depletion)
    depletion = initial_depletion
    for et0_i, kc_i, p_i in zip(et0, kc, precip):
        runoff = scs_runoff(p_i, curve_number)
        infiltration = p_i - runoff
        etc = kc_i * et0_i
        p = adjusted_depletion_fraction(p_table, etc) if adjust_p else p_table
        after_rain = max(depletion - infiltration, 0.0)
        irrigation = after_rain if irrigate and after_rain >= p * taw and after_rain > 0.0 else 0.0
        start = max(after_rain - irrigation, 0.0)  # Dr,i start (FAO-56 Example 36, column 5)
        ks = water_stress_coefficient(start, taw, p)
        eta = min(ks * etc, taw - start)  # cannot transpire water that is not stored
        # Eqs. 85 and 88 with CR = 0: water above field capacity drains, and depletion is then exactly 0.
        balance = depletion - infiltration - irrigation + eta
        drainage, depletion = (-balance, 0.0) if balance < 0.0 else (0.0, balance)

        r.precipitation += p_i
        r.runoff += runoff
        r.irrigation_net += irrigation
        r.irrigation_events += irrigation > 0.0
        r.etc_standard += etc
        r.eta += eta
        r.drainage += drainage
        r.stress_days += ks < 1.0
        r.daily_ks.append(ks)
        r.daily_depletion.append(depletion)
    r.final_depletion = depletion
    storage_change = (taw - r.final_depletion) - (taw - r.initial_depletion)
    r.closure_residual = r.precipitation - r.runoff + r.irrigation_net - r.eta - r.drainage - storage_change
    if not math.isfinite(r.closure_residual):
        raise ValueError("water balance produced a non-finite value")
    return r
