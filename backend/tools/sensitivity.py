"""One-at-a-time sensitivity of season outputs to the engine's assumptions (Phase 3 audit).

Usage (from backend/): python tools/sensitivity.py <site> <output.json>
Each case changes one assumption and reruns all 25 seasons for every crop; the table reports medians.
This shows how much each assumption can move the results. It is not validation, and no case is "correct".
"""
import json
import statistics
import sys
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from snapshot_medians import site_inputs  # noqa: E402

from app.adapters import ssurgo  # noqa: E402
from app.adapters.power import DailyWeather  # noqa: E402
from app.domain.crop_catalog import load_catalog  # noqa: E402
from app.science.crop import Horizon, layered_total_available_water  # noqa: E402
from app.services.analysis_v2 import simulate_season  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUTPUTS = ["etc_standard", "rainfed_deficit", "rainfed_stress_days", "irrigated_net_irrigation"]


def components(site: str) -> dict[str, tuple[list[Horizon], str]]:
    """Every component with water data in the map unit: name -> (horizons up to the first missing AWC, group)."""
    raw = json.loads((ROOT / "data" / "validation" / "raw" / f"ssurgo_allcomponents_{site}.json").read_text("utf-8"))
    out: dict[str, tuple[list[Horizon], str]] = {}
    stopped: set[str] = set()
    for r in raw["response"]["Table"][1:]:
        row = dict(zip(ssurgo.COLUMNS, r))
        name = f"{row['compname']} ({row['comppct_r']}%)"
        if row["awc_r"] is None or row["hzdept_r"] is None or name in stopped:
            stopped.add(name)
            continue
        horizons, _ = out.setdefault(name, ([], (row["hydgrp"] or "").split("/")[-1]))
        horizons.append(Horizon(float(row["hzdept_r"]), float(row["hzdepb_r"]), float(row["awc_r"])))
    return {k: v for k, v in out.items() if v[0] and v[1] in ssurgo.CURVE_NUMBERS}


def tdew_from_tmin(weather: DailyWeather) -> DailyWeather:
    """FAO-56 Eq. 48: when humidity data are questionable, Tdew ≈ Tmin (here only as a sensitivity case)."""
    return replace(weather, values={**weather.values, "t_dew": list(weather.values["t_min"])})


def run(crop, weather, taw, cn, depletion=0.5, shift_days=0, **kwargs) -> dict:
    index = {d: i for i, d in enumerate(weather.dates)}
    month, day = (int(x) for x in crop.planting_default.split("-"))
    seasons = []
    for year in range(2001, 2026):
        status, o = simulate_season(crop, weather, index, date(year, month, day) + timedelta(days=shift_days), taw, cn,
                                    depletion, **kwargs)
        if status == "ok":
            seasons.append(o)
    return {"n": len(seasons), "taw_mm": round(taw, 1),
            **{k: round(statistics.median(getattr(o, k) for o in seasons), 1) if seasons else None for k in OUTPUTS}}


def main(site: str, out: str) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    lon, lat, weather, profile = site_inputs(site)
    limits = json.loads((ROOT / "data" / "fixtures" / f"ssurgo_restrictions_{site}.json").read_text("utf-8"))
    profile = ssurgo.apply_restrictions(profile, limits["response"], limits["retrieved_utc"])
    comps = components(site)
    result = {"site": site, "soil": profile.component, "curve_number": profile.curve_number, "crops": {}}
    for crop in load_catalog().crops.values():
        def taw_for(horizons, depth_m):
            return layered_total_available_water(horizons, min(depth_m, horizons[-1].bottom_cm / 100.0, profile.depth_cm / 100.0))

        base_taw = taw_for(profile.horizons, crop.root_depth_m)
        cn = profile.curve_number
        lo, hi = crop.root_depth_range_m
        cases = {
            "base (documented method)": run(crop, weather, base_taw, cn),
            f"root depth {lo} m (Table 22 minimum)": run(crop, weather, taw_for(profile.horizons, lo), cn),
            f"root depth {hi} m (Table 22 maximum)": run(crop, weather, taw_for(profile.horizons, hi), cn),
            "root depth 0.3 m all season (early-season roots, bounding case)": run(crop, weather, taw_for(profile.horizons, 0.3), cn),
            "start at field capacity (depletion 0)": run(crop, weather, base_taw, cn, depletion=0.0),
            "start 0.25 TAW depleted": run(crop, weather, base_taw, cn, depletion=0.25),
            "start 0.75 TAW depleted": run(crop, weather, base_taw, cn, depletion=0.75),
            "planting 15 days earlier": run(crop, weather, base_taw, cn, shift_days=-15),
            "planting 15 days later": run(crop, weather, base_taw, cn, shift_days=15),
            "no Kc climate adjustment (Eqs. 62, 65 off)": run(crop, weather, base_taw, cn, adjust_kc=False),
            "irrigate at 0.5 RAW, refill to field capacity": run(crop, weather, base_taw, cn, trigger_fraction=0.5),
            "irrigate at RAW, refill to 0.5 RAW": run(crop, weather, base_taw, cn, refill_fraction=0.5),
            "ea from Tdew = Tmin (FAO-56 Eq. 48)": run(crop, tdew_from_tmin(weather), base_taw, cn),
        }
        if profile.fc_wp_horizons:
            cases["TAW from θ(1/3 bar) - θ(15 bar) instead of awc_r"] = run(
                crop, weather, taw_for(profile.fc_wp_horizons, crop.root_depth_m), cn)
        for name, (horizons, group) in comps.items():
            if not name.startswith(profile.component):
                cases[f"soil component {name}, group {group}"] = run(
                    crop, weather, layered_total_available_water(horizons, min(crop.root_depth_m, horizons[-1].bottom_cm / 100)),
                    ssurgo.CURVE_NUMBERS[group])
        result["crops"][crop.id] = cases
    Path(out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    for crop_id, cases in result["crops"].items():
        print(f"\n{site} {crop_id}")
        for name, r in cases.items():
            print(f"  {name:62s} TAW {r['taw_mm']:6} ETc {r['etc_standard']}  deficit {r['rainfed_deficit']}  "
                  f"stress {r['rainfed_stress_days']}  net irr {r['irrigated_net_irrigation']}  n={r['n']}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
