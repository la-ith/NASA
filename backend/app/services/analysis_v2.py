"""Field Shift v4 analysis engine: historical weather replay of crop strategies (spec v4.0, sections 5-7).

For every candidate crop and every complete past season, using that season's real daily NASA POWER weather:

  1. ET0 each day by FAO-56 Penman-Monteith (Eq. 6), with ea from dewpoint (Eq. 14), Rs from POWER all-sky
     shortwave, u2 from POWER 2 m wind and γ from POWER surface pressure (Eq. 8).
  2. Kc each day from the FAO-56 stage curve (Eq. 66), with Kc mid and Kc end adjusted for that season's
     mid-season wind and minimum humidity (Eqs. 62, 63, 65).
  3. Standard crop demand ETc = Kc ET0 (Eq. 58).
  4. The daily root-zone water balance (Eqs. 80-88) twice: rain-fed (missing water stays a deficit) and
     irrigated (net irrigation refills the root zone when RAW is depleted).

The spread of these season results is a historical scenario ensemble. It is not a forecast and not a probability
of crop success, and it says nothing about yield or profit (spec v4.0, section 6).
"""
import math
from dataclasses import asdict, dataclass
from datetime import date, timedelta

from app.adapters.power import DailyWeather
from app.adapters.ssurgo import CURVE_NUMBERS, SoilProfile
from app.domain.crop_catalog import Catalog, CropProfileV2
from app.science import fao56
from app.science.crop import adjust_kc_for_climate, kc_curve, layered_total_available_water, min_relative_humidity
from app.science.statistics import spread
from app.science.water_balance import simulate

ENGINE_VERSION = "2.0.0"
CLOSURE_TOLERANCE_MM = 1e-6  # floating-point only; the balance is algebraically exact
NEEDED = ("t_max", "t_min", "t_dew", "wind_2m", "shortwave_down", "surface_pressure", "precipitation", "t_mean")


@dataclass(frozen=True)
class SoilInput:
    """Root-zone soil description used by the water balance, with where it came from."""
    source: str  # "ssurgo" or "user"
    awc_by_horizon: list  # list[Horizon]
    hydrologic_group: str
    depth_cm: float
    label: str
    fc_wp_by_horizon: list  # for the sensitivity check; empty for user input
    manifest: dict | None = None  # source record for SSURGO soil; None for user input

    @property
    def curve_number(self) -> int:
        return CURVE_NUMBERS[self.hydrologic_group]


def soil_from_ssurgo(profile: SoilProfile) -> SoilInput:
    return SoilInput("ssurgo", profile.horizons, profile.hydrologic_group, profile.depth_cm,
                     f"{profile.component} ({profile.map_unit}; {profile.component_percent:g}% of map unit "
                     f"{profile.mukey}; hydrologic group {profile.hydrologic_group_raw})", profile.fc_wp_horizons,
                     profile.manifest)


def planting_date(year: int, month_day: str) -> date:
    month, day = (int(x) for x in month_day.split("-"))
    return date(year, month, day)


@dataclass
class SeasonOutcome:
    year: int
    planting: str
    harvest: str
    et0: float
    etc_standard: float
    precipitation: float
    runoff: float
    rainfed_eta: float
    rainfed_deficit: float
    rainfed_stress_days: int
    rainfed_drainage: float
    irrigated_net_irrigation: float
    irrigated_events: int
    kc_mid_adjusted: float
    kc_end_adjusted: float
    max_closure_residual: float


def simulate_season(crop: CropProfileV2, weather: DailyWeather, index: dict[date, int], start: date, taw: float,
                    curve_number: int, initial_depletion_fraction: float) -> tuple[str, SeasonOutcome | str]:
    """One season. Returns ("ok", outcome) or (status, reason) when the season cannot be simulated."""
    days = [start + timedelta(days=k) for k in range(crop.stages.total)]
    if days[0] not in index or days[-1] not in index:
        return "outside_record", "the season is not fully inside the weather record"
    rows = [index[d] for d in days]
    v = weather.values
    if any(v[q][i] is None for q in NEEDED for i in rows):
        return "missing_data", "a needed weather value is missing (NASA fill value)"
    if any(v["t_mean"][i] <= 0.0 for i in rows):
        return "frozen_conditions", "a day with mean air temperature at or below 0 °C (snow or frozen soil possible)"

    et0_days = [fao56.daily_et0(d, weather.latitude, v["t_max"][i], v["t_min"][i],
                                fao56.actual_vapour_pressure_from_dewpoint(v["t_dew"][i]), v["shortwave_down"][i],
                                v["wind_2m"][i], v["surface_pressure"][i], weather.cell_elevation_m)
                for d, i in zip(days, rows)]
    if any(not math.isfinite(e.et0_mm) for e in et0_days):
        return "outside_applicability", "ET0 undefined on a day without daylight (polar night)"
    et0 = [e.et0_mm for e in et0_days]

    s = crop.stages
    mid_rows = rows[s.initial + s.development: s.initial + s.development + s.mid]
    u2_mid = sum(v["wind_2m"][i] for i in mid_rows) / len(mid_rows)
    rhmin_mid = sum(min_relative_humidity(v["t_dew"][i], v["t_max"][i]) for i in mid_rows) / len(mid_rows)
    kc_mid = adjust_kc_for_climate(crop.kc_mid, u2_mid, rhmin_mid, crop.height_m).kc
    kc_end = adjust_kc_for_climate(crop.kc_end, u2_mid, rhmin_mid, crop.height_m).kc if crop.kc_end >= 0.45 \
        else crop.kc_end
    kc = kc_curve(s, crop.kc_ini, kc_mid, kc_end)
    precip = [v["precipitation"][i] for i in rows]
    initial = initial_depletion_fraction * taw
    rainfed = simulate(et0, kc, precip, taw, crop.p, curve_number, initial, irrigate=False)
    irrigated = simulate(et0, kc, precip, taw, crop.p, curve_number, initial, irrigate=True)
    residual = max(abs(rainfed.closure_residual), abs(irrigated.closure_residual))
    if residual > CLOSURE_TOLERANCE_MM:
        raise ArithmeticError(f"water balance did not close ({residual} mm) in {days[0].year}")
    return "ok", SeasonOutcome(
        days[0].year, days[0].isoformat(), days[-1].isoformat(), sum(et0), rainfed.etc_standard,
        rainfed.precipitation, rainfed.runoff, rainfed.eta, rainfed.deficit, rainfed.stress_days, rainfed.drainage,
        irrigated.irrigation_net, irrigated.irrigation_events, kc_mid, kc_end, residual)


SUMMARIZED = {  # output -> (unit, result type)
    "et0": ("mm per season", "historical_analysis"),
    "etc_standard": ("mm per season", "historical_analysis"),
    "precipitation": ("mm per season", "historical_analysis"),
    "rainfed_eta": ("mm per season", "conditional_simulation"),
    "rainfed_deficit": ("mm per season", "conditional_simulation"),
    "rainfed_stress_days": ("days per season", "conditional_simulation"),
    "irrigated_net_irrigation": ("mm per season", "conditional_simulation"),
}


def replay_strategy(crop: CropProfileV2, weather: DailyWeather, soil: SoilInput | None, years: range,
                    planting: str, initial_depletion_fraction: float) -> dict:
    index = {d: i for i, d in enumerate(weather.dates)}
    root_depth = min(crop.root_depth_m, soil.depth_cm / 100.0) if soil else crop.root_depth_m
    taw = layered_total_available_water(soil.awc_by_horizon, root_depth) if soil else None
    taw_fc_wp = layered_total_available_water(soil.fc_wp_by_horizon, root_depth) if soil and soil.fc_wp_by_horizon \
        else None
    outcomes, excluded = [], {}
    for year in years:
        start = planting_date(year, planting)
        if soil is None:
            status, result = simulate_climate_only(crop, weather, index, start)
        else:
            status, result = simulate_season(crop, weather, index, start, taw, soil.curve_number,
                                             initial_depletion_fraction)
        if status == "ok":
            outcomes.append(result)
        else:
            excluded.setdefault(status, {"count": 0, "reason": result, "years": []})
            excluded[status]["count"] += 1
            excluded[status]["years"].append(year)
    summaries = {}
    for name, (unit, result_type) in SUMMARIZED.items():
        values = [getattr(o, name) for o in outcomes if getattr(o, name) is not None]
        stats = spread(values)
        summaries[name] = {"unit": unit, "result_type": result_type,
                           "spread": None if stats is None else {k: round(x, 1) if isinstance(x, float) else x
                                                                 for k, x in asdict(stats).items()}}
    return {
        "taw_mm": None if taw is None else round(taw, 1),
        "taw_fc_wp_mm": None if taw_fc_wp is None else round(taw_fc_wp, 1),
        "raw_mm": None if taw is None else round(crop.p * taw, 1),
        "root_depth_m": root_depth,
        "seasons_simulated": len(outcomes),
        "seasons_excluded": excluded,
        "summary": summaries,
        "seasons": [{k: (round(x, 2) if isinstance(x, float) else x) for k, x in asdict(o).items()} for o in outcomes],
        "max_closure_residual_mm": max((o.max_closure_residual for o in outcomes), default=None),
    }


def simulate_climate_only(crop: CropProfileV2, weather: DailyWeather, index: dict[date, int],
                          start: date) -> tuple[str, SeasonOutcome | str]:
    """Without soil data the water balance cannot run; ET0, crop demand and rainfall are still computed."""
    days = [start + timedelta(days=k) for k in range(crop.stages.total)]
    if days[0] not in index or days[-1] not in index:
        return "outside_record", "the season is not fully inside the weather record"
    rows = [index[d] for d in days]
    v = weather.values
    if any(v[q][i] is None for q in NEEDED for i in rows):
        return "missing_data", "a needed weather value is missing (NASA fill value)"
    et0 = [fao56.daily_et0(d, weather.latitude, v["t_max"][i], v["t_min"][i],
                           fao56.actual_vapour_pressure_from_dewpoint(v["t_dew"][i]), v["shortwave_down"][i],
                           v["wind_2m"][i], v["surface_pressure"][i], weather.cell_elevation_m).et0_mm
           for d, i in zip(days, rows)]
    kc = kc_curve(crop.stages, crop.kc_ini, crop.kc_mid, crop.kc_end)
    etc = sum(k * e for k, e in zip(kc, et0))
    precip = sum(v["precipitation"][i] for i in rows)
    return "ok", SeasonOutcome(days[0].year, days[0].isoformat(), days[-1].isoformat(), sum(et0), etc, precip,
                               None, None, None, None, None, None, None, crop.kc_mid, crop.kc_end, 0.0)


# ---------- strategies ----------
ROTATION_NOTES = {  # qualitative, draft; no quantified benefit is claimed (spec v4.0, section 5.5)
    "same_crop": "Same crop as the last recorded season (continuous cropping). Extension guidance commonly associates "
                 "this with more pest and disease carry-over; local evidence needed.",
    "legume_after_cereal": "A legume after a cereal breaks the cereal sequence and fixes atmospheric nitrogen; "
                           "no nitrogen credit is calculated here.",
    "cereal_after_legume": "A cereal after a legume follows the common Corn Belt alternation.",
    "cereal_after_cereal": "A different cereal after a cereal keeps a cereal sequence (crop family unchanged).",
    "unknown_previous": "The last season's crop is unknown, so no rotation note applies.",
    "outside_catalog_previous": "The last season's crop is outside the catalog, so its crop family is unknown and "
                                "no rotation note applies.",
}


def rotation_note(crop: CropProfileV2, last_crop: str | None, catalog: Catalog) -> dict:
    if last_crop in (None, "unknown"):
        key = "unknown_previous"
    elif last_crop == crop.id:
        key = "same_crop"
    elif last_crop not in catalog.crops:
        key = "outside_catalog_previous"
    else:
        last_family = catalog.crops[last_crop].family if last_crop in catalog.crops else None
        key = {("legume", "cereal"): "legume_after_cereal", ("cereal", "legume"): "cereal_after_legume",
               ("cereal", "cereal"): "cereal_after_cereal"}.get((crop.family, last_family), "unknown_previous")
    return {"key": key, "text": ROTATION_NOTES[key], "review_state": "draft-unreviewed",
            "scope": "U.S. Great Plains and Corn Belt pilot", "quantified": False}


def build_strategies(catalog: Catalog, current: str | None, requested: list[str] | None) -> tuple[list[dict], list[dict]]:
    """Current practice first, then alternatives; unsupported crops are rejected with a reason, never replaced."""
    wanted = requested or [current] + [c for c in catalog.crops if c != current]
    strategies, rejected = [], []
    for k, crop_id in enumerate(dict.fromkeys(c for c in wanted if c)):
        if crop_id not in catalog.crops:
            rejected.append({"crop": crop_id, "reason": "This crop is not in the U.S. catalog for this release."})
            continue
        strategies.append({"id": f"S{len(strategies) + 1}", "crop": crop_id,
                           "role": "current_practice" if crop_id == current else "alternative"})
    return strategies, rejected
