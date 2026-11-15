"""Season-by-stage diagnostic breakdown of one crop at one saved site (Phase 3 audit).

Usage (from backend/): python tools/diagnose_site.py <site> <crop_id> <output_prefix>
  site: ks_hays, ia_ames or ca_fresno (saved fixtures in data/fixtures). Writes <prefix>.csv (one row per season and
  growth stage) and <prefix>.json (medians per stage). Uses the engine's own functions, so it reproduces the analysis.
"""
import csv
import json
import statistics
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from snapshot_medians import site_inputs  # noqa: E402

from app.adapters import ssurgo  # noqa: E402
from app.domain.crop_catalog import load_catalog  # noqa: E402
from app.science import fao56  # noqa: E402
from app.science.crop import adjust_kc_for_climate, kc_curve, layered_total_available_water, min_relative_humidity  # noqa: E402
from app.science.water_balance import simulate  # noqa: E402
from app.services.analysis_v2 import stage_climate_means  # noqa: E402

FIXTURES = Path(__file__).resolve().parents[2] / "data" / "fixtures"


def main(site: str, crop_id: str, prefix: str) -> None:
    lon, lat, weather, profile = site_inputs(site)
    limits = json.loads((FIXTURES / f"ssurgo_restrictions_{site}.json").read_text(encoding="utf-8"))
    profile = ssurgo.apply_restrictions(profile, limits["response"], limits["retrieved_utc"])
    crop = load_catalog().crops[crop_id]
    s = crop.stages
    root = min(crop.root_depth_m, profile.depth_cm / 100.0)
    taw = layered_total_available_water(profile.horizons, root)
    index = {d: i for i, d in enumerate(weather.dates)}
    v = weather.values
    stages = [("initial", 0, s.initial), ("development", s.initial, s.initial + s.development),
              ("mid", s.initial + s.development, s.initial + s.development + s.mid), ("late", s.total - s.late, s.total)]
    month, day = (int(x) for x in crop.planting_default.split("-"))
    rows = []
    for year in range(2001, 2026):
        days = [date(year, month, day) + timedelta(days=k) for k in range(s.total)]
        ii = [index[d] for d in days]
        if any(v["t_mean"][i] <= 0 for i in ii):
            continue
        et0 = [fao56.daily_et0(d, lat, v["t_max"][i], v["t_min"][i], fao56.actual_vapour_pressure_from_dewpoint(v["t_dew"][i]),
                               v["shortwave_down"][i], v["wind_2m"][i], v["surface_pressure"][i], weather.cell_elevation_m)
               for d, i in zip(days, ii)]
        mid_rows = ii[s.initial + s.development: s.initial + s.development + s.mid]
        adj_mid = adjust_kc_for_climate(crop.kc_mid, *stage_climate_means(weather, mid_rows), crop.height_m)
        kc_end = adjust_kc_for_climate(crop.kc_end, *stage_climate_means(weather, ii[s.total - s.late:]), crop.height_m).kc \
            if crop.kc_end >= 0.45 else crop.kc_end
        kc_adj = kc_curve(s, crop.kc_ini, adj_mid.kc, kc_end)
        kc_tab = kc_curve(s, crop.kc_ini, crop.kc_mid, crop.kc_end)
        e0 = [x.et0_mm for x in et0]
        precip = [v["precipitation"][i] for i in ii]
        rainfed = simulate(e0, kc_adj, precip, taw, crop.p, profile.curve_number, 0.5 * taw)
        irrigated = simulate(e0, kc_adj, precip, taw, crop.p, profile.curve_number, 0.5 * taw, irrigate=True)
        for name, a, b in stages:
            idx = ii[a:b]
            mean = lambda q: statistics.fmean(v[q][i] for i in idx)  # noqa: E731
            rf, ir = rainfed.daily[a:b], irrigated.daily[a:b]
            rows.append({
                "year": year, "stage": name, "days": b - a, "start": days[a].isoformat(),
                "t_max_c": mean("t_max"), "t_min_c": mean("t_min"), "t_dew_c": mean("t_dew"),
                "rh_min_pct": statistics.fmean(min_relative_humidity(v["t_dew"][i], v["t_max"][i]) for i in idx),
                "u2_ms": mean("wind_2m"), "rs_mj": mean("shortwave_down"), "ps_kpa": mean("surface_pressure"),
                "rn_mj": statistics.fmean(x.rn for x in et0[a:b]), "vpd_kpa": statistics.fmean(x.es_kpa - x.ea_kpa for x in et0[a:b]),
                "et0_mm": sum(e0[a:b]), "et0_mm_day": statistics.fmean(e0[a:b]),
                "kc_table_mean": statistics.fmean(kc_tab[a:b]), "kc_adjusted_mean": statistics.fmean(kc_adj[a:b]),
                "kc_mid_limited": adj_mid.limited,
                "etc_standard_mm": sum(d["etc"] for d in rf), "rainfed_eta_mm": sum(d["eta"] for d in rf),
                "rain_mm": sum(precip[a:b]), "runoff_mm": sum(d["runoff"] for d in rf),
                "rainfed_drainage_mm": sum(d["drainage"] for d in rf),
                "irrigation_net_mm": sum(d["irrigation"] for d in ir), "irrigation_events": sum(d["irrigation"] > 0 for d in ir),
                "irrigated_drainage_mm": sum(d["drainage"] for d in ir),
                "storage_start_mm": taw - (rainfed.initial_depletion if a == 0 else rainfed.daily[a - 1]["dr_end"]),
                "storage_end_mm": taw - rf[-1]["dr_end"], "taw_mm": taw,
            })
    with open(f"{prefix}.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows({k: round(x, 3) if isinstance(x, float) else x for k, x in r.items()} for r in rows)
    medians = {name: {k: round(statistics.median(r[k] for r in rows if r["stage"] == name), 2)
                      for k in rows[0] if isinstance(rows[0][k], (int, float)) and not isinstance(rows[0][k], bool) and k != "year"}
               for name, _, _ in stages}
    seasons = sorted({r["year"] for r in rows})
    totals = {k: round(statistics.median(sum(r[k] for r in rows if r["year"] == y) for y in seasons), 1)
              for k in ["et0_mm", "etc_standard_mm", "rainfed_eta_mm", "rain_mm", "runoff_mm", "irrigation_net_mm"]}
    summary = {"site": site, "crop": crop_id, "taw_mm": taw, "root_depth_m": root, "curve_number": profile.curve_number,
               "seasons": len(seasons), "kc_mid_limited_seasons": sum(r["kc_mid_limited"] for r in rows if r["stage"] == "mid"),
               "season_total_medians": totals, "stage_medians": medians}
    Path(f"{prefix}.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in summary if k != "stage_medians"}, indent=1))
    for name in medians:
        m = medians[name]
        print(name, {k: m[k] for k in ["t_max_c", "t_dew_c", "rh_min_pct", "u2_ms", "rs_mj", "et0_mm_day", "kc_table_mean",
                                       "kc_adjusted_mean", "etc_standard_mm", "irrigation_net_mm"]})


if __name__ == "__main__":
    main(*sys.argv[1:4])
