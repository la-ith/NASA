"""Builds one complete v4 analysis from validated inputs: strategies, replay, input states, summary, limits.

Pure: weather and soil arrive already fetched and validated, so this runs offline in tests and the CLI.
"""
from datetime import date

from app.adapters.power import DailyWeather
from app.domain.crop_catalog import Catalog
from app.geo.boundaries import BOUNDARY_VERSION, State
from app.services.analysis_v2 import (ENGINE_VERSION, SoilInput, build_strategies, replay_strategy, rotation_note)

GOAL_ORDER = {  # the goal orders the outputs and picks the summary; it never changes a calculated number
    "conserve_water": ["irrigated_net_irrigation", "rainfed_deficit", "rainfed_stress_days", "etc_standard"],
    "reduce_drought_stress": ["rainfed_deficit", "rainfed_stress_days", "irrigated_net_irrigation", "etc_standard"],
    "improve_soil_rotation": ["rotation", "rainfed_deficit", "irrigated_net_irrigation", "etc_standard"],
}
OUTPUT_NAME = {
    "et0": "Reference evapotranspiration ET0", "etc_standard": "Standard crop water demand ETc",
    "precipitation": "Season rainfall", "rainfed_eta": "Rain-fed actual ET", "rainfed_deficit": "Rain-fed water deficit",
    "rainfed_stress_days": "Rain-fed water-stress days", "irrigated_net_irrigation": "Net irrigation requirement",
}


def input_states(request: dict, soil: SoilInput | None, catalog: Catalog) -> list[dict]:
    """The "What we know" labels: entered, estimated, assumed or missing, each with its source and effect."""
    items = [{"name": "location", "state": "entered", "source": "user",
              "effect": "Selects the NASA POWER grid cell and the SSURGO map unit."}]
    history = request.get("history", [])
    if history:
        for h in history:
            known = h["crop"] != "unknown"
            items.append({"name": f"crop {h['year']}", "state": "entered" if known else "missing",
                          "source": h.get("provenance", "farmer"),
                          "effect": "Used for the rotation note." if known else "No rotation note can use this season."})
    else:
        items.append({"name": "crop history", "state": "missing", "source": None,
                      "effect": "No rotation note is possible; water results are unaffected."})
    irrigation = request.get("irrigation", "unknown")
    items.append({"name": "irrigation", "state": "missing" if irrigation == "unknown" else "entered", "source": "user",
                  "effect": "Both the rain-fed and the irrigated scenario are shown; neither is assumed to be yours."
                  if irrigation == "unknown" else f"The {irrigation} scenario is shown first."})
    if soil is None:
        items.append({"name": "soil water capacity", "state": "missing", "source": None,
                      "effect": "The water balance cannot run; only ET0, crop demand and rainfall are shown."})
    else:
        items.append({"name": "soil water capacity", "state": "estimated" if soil.source == "ssurgo" else "entered",
                      "source": soil.label, "effect": "Sets TAW and RAW for the water balance (FAO-56 Eqs. 82-83)."})
        items.append({"name": "runoff curve number", "state": "estimated" if soil.source == "ssurgo" else "entered",
                      "source": f"TR-55 row crops, straight row, good condition, group {soil.hydrologic_group}: "
                                f"CN {soil.curve_number}", "effect": "Splits rain into runoff and infiltration."})
    planting = request.get("planting_dates", {})
    for crop_id, crop in catalog.crops.items():
        items.append({"name": f"{crop.name} planting date",
                      "state": "entered" if crop_id in planting else "assumed",
                      "source": planting.get(crop_id) or f"default {crop.planting_default}",
                      "effect": "Fixes the dates of every simulated season."})
    items.append({"name": "starting soil water", "state": "entered" if "initial_depletion_fraction" in request else "assumed",
                  "source": f"{request.get('initial_depletion_fraction', 0.5):g} of TAW depleted at planting",
                  "effect": "Sets the water already used up when each season starts."})
    items.append({"name": "crop coefficients and stages", "state": "estimated",
                  "source": f"FAO-56 Tables 11, 12 and 22 (catalog {catalog.version})",
                  "effect": "Not calibrated for local hybrids or varieties."})
    return items


def summary_text(goal: str, strategies: list[dict], catalog: Catalog) -> str:
    """Names the goal's first numeric output for every strategy, by median; ranks nothing."""
    order = [o for o in GOAL_ORDER[goal] if o != "rotation"]
    parts = []
    for output in order[:2]:
        values = [(catalog.crops[s["crop"]].name, s["result"]["summary"][output]["spread"]) for s in strategies]
        if all(v is None for _, v in values):
            parts.append(f"{OUTPUT_NAME[output]} could not be calculated for any strategy.")
            continue
        listed = "; ".join(f"{name} {v['median']:g}" if v else f"{name} unavailable" for name, v in values)
        unit = strategies[0]["result"]["summary"][output]["unit"]
        parts.append(f"Median {OUTPUT_NAME[output].lower()} ({unit}): {listed}.")
    return " ".join(parts) + " Historical weather replay, not a forecast."


def run_analysis(request: dict, state: State, weather: DailyWeather, soil: SoilInput | None, catalog: Catalog,
                 mode: str) -> dict:
    years = range(request["start_year"], request["end_year"] + 1)
    history = sorted(request.get("history", []), key=lambda h: h["year"])
    last_crop = history[-1]["crop"] if history else None
    current = request.get("current_practice") or (last_crop if last_crop in catalog.crops else None)
    strategies, rejected = build_strategies(catalog, current, request.get("candidates"))
    for s in strategies:
        crop = catalog.crops[s["crop"]]
        planting = request.get("planting_dates", {}).get(s["crop"], crop.planting_default)
        s["name"] = crop.name
        s["planting"] = planting
        s["why_included"] = ("Current practice: the crop you grow now." if s["role"] == "current_practice"
                             else f"Alternative: a supported {crop.family} in the U.S. catalog for the same season.")
        s["rotation"] = rotation_note(crop, last_crop, catalog)
        s["result"] = replay_strategy(crop, weather, soil, years, planting,
                                      request.get("initial_depletion_fraction", 0.5))
        s["parameters"] = {"kc_ini": crop.kc_ini, "kc_mid_table": crop.kc_mid, "kc_end_table": crop.kc_end,
                           "stages_days": [crop.stages.initial, crop.stages.development, crop.stages.mid, crop.stages.late],
                           "height_m": crop.height_m, "p": crop.p, "sources": crop.sources}
    simulated = [s["result"]["seasons_simulated"] for s in strategies]
    status = "complete" if strategies and soil and all(n > 0 for n in simulated) else "partial"
    if not strategies or not any(simulated):
        status = "unsupported"
    limitations = [
        "Historical weather replay: each strategy is run under the same past seasons. This is not a forecast and not a "
        "probability of crop success; it says nothing about yield or profit.",
        f"Weather is one NASA POWER grid cell (meteorology about 0.5° × 0.625°, radiation 1°), mean elevation "
        f"{weather.cell_elevation_m:.0f} m: regional, not a field measurement.",
        "Water balance assumptions: constant rooting depth from planting, no capillary rise, curve number for average "
        "antecedent moisture, irrigation refills to field capacity when RAW is depleted (net, no application losses).",
        "Crop parameters are FAO-56 tabulated values, not calibrated for local hybrids, and are labelled draft until "
        "an agronomist reviews them.",
    ]
    if soil is None:
        limitations.append("No soil data: the water balance could not run, so deficits and irrigation needs are missing.")
    elif soil.source == "ssurgo":
        limitations.append("Soil is the dominant component of the SSURGO map unit; other soils in the map unit can "
                           "differ. TAW from NRCS available water capacity; the 1/3-15 bar alternative is shown "
                           "as a sensitivity check.")
    if mode == "sample":
        limitations.append("Sample mode: saved NASA and USDA records, not a live retrieval.")
    if not current:
        limitations.append("Current practice is unknown, so no strategy is labelled as current practice.")
    if len(strategies) < 3:
        limitations.append(f"Only {len(strategies)} eligible strategies: fewer than the three the challenge asks for.")
    return {
        "schema_version": "2.0", "status": status, "mode": mode, "result_types": {
            "historical_analysis": "Indicators from past data (ET0, crop demand, rainfall).",
            "conditional_simulation": "Water balance under each past season's weather and stated management.",
            "validated_prediction": "None in this release."},
        "location": {"state": state.code, "state_name": state.name, "boundary_version": BOUNDARY_VERSION,
                     "public_location": {"lat": round(request["lat"], 1), "lon": round(request["lon"], 1)}},
        "period": {"requested": [years.start, years.stop - 1], "weather_record": [weather.dates[0].isoformat(),
                                                                                    weather.dates[-1].isoformat()]},
        "goal": request["goal"], "output_order": GOAL_ORDER[request["goal"]],
        "summary": summary_text(request["goal"], strategies, catalog) if strategies else "No eligible strategy.",
        "strategies": strategies, "rejected": rejected,
        "soil": None if soil is None else {"source": soil.source, "label": soil.label,
                                           "hydrologic_group": soil.hydrologic_group, "curve_number": soil.curve_number,
                                           "depth_cm": soil.depth_cm},
        "inputs": input_states(request, soil, catalog),
        "limitations": limitations,
        "provenance": {"weather": weather.manifest, "soil": None if soil is None else soil.manifest},
        "versions": {"engine": ENGINE_VERSION, "crop_catalog": catalog.version, "boundary": BOUNDARY_VERSION},
        "equations": ["FAO56-Eq6", "FAO56-Eq8", "FAO56-Eq9", "FAO56-Eq11", "FAO56-Eq12", "FAO56-Eq13", "FAO56-Eq14",
                      "FAO56-Eq21", "FAO56-Eq23", "FAO56-Eq24", "FAO56-Eq25", "FAO56-Eq37", "FAO56-Eq38",
                      "FAO56-Eq39", "FAO56-Eq40", "FAO56-Eq42", "FAO56-Eq58", "FAO56-Eq62", "FAO56-Eq63",
                      "FAO56-Eq65", "FAO56-Eq66", "FAO56-Eq80", "FAO56-Eq82", "FAO56-Eq83", "FAO56-Eq84",
                      "FAO56-Eq85", "FAO56-Eq88", "FAO56-T22-p", "SCS-CN", "BALANCE"],
        "generated": date.today().isoformat(),
    }
