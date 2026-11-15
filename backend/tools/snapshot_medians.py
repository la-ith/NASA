"""Record the engine's median outputs at the saved demo/diagnostic sites, for before/after comparisons.

Usage: python tools/snapshot_medians.py <output.json>   (from the backend folder; offline, saved fixtures only)
"""
import json
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.adapters import power, ssurgo  # noqa: E402
from app.domain.crop_catalog import load_catalog  # noqa: E402
from app.geo.boundaries import state_at  # noqa: E402
from app.services.analysis_v2 import ENGINE_VERSION, soil_from_ssurgo  # noqa: E402
from app.services.run_v2 import run_analysis  # noqa: E402

FIXTURES = Path(__file__).resolve().parents[2] / "data" / "fixtures"
SITES = {"ks_hays": (-99.33, 38.85), "ia_ames": (-93.62, 42.03), "ca_fresno": (-119.79, 36.74)}
OUTPUTS = ["et0", "etc_standard", "rainfed_deficit", "rainfed_stress_days", "irrigated_net_irrigation"]


def site_inputs(site: str):
    lon, lat = SITES[site]
    w = json.loads((FIXTURES / f"power_{site}_2001_2025.json").read_text(encoding="utf-8"))
    s = json.loads((FIXTURES / f"ssurgo_{site}.json").read_text(encoding="utf-8"))
    weather = power.validate_and_normalize(w["response"], lon, lat, date(2001, 1, 1), date(2025, 12, 31),
                                           datetime.fromisoformat(w["retrieved_utc"]))
    profile = ssurgo.validate_and_normalize(s["response"], lon, lat, s["retrieved_utc"])
    return lon, lat, weather, profile


def main(out: str) -> None:
    snapshot = {"engine": ENGINE_VERSION, "sites": {}}
    for site, (lon, lat) in SITES.items():
        _, _, weather, profile = site_inputs(site)
        request = {"lat": lat, "lon": lon, "start_year": 2001, "end_year": 2025, "goal": "conserve_water"}
        result = run_analysis(request, state_at(lon, lat), weather, soil_from_ssurgo(profile), load_catalog(), "sample")
        snapshot["sites"][site] = {
            s["crop"]: {"taw_mm": s["result"]["taw_mm"], "root_depth_m": s["result"]["root_depth_m"],
                        **{o: s["result"]["summary"][o]["spread"]["median"] for o in OUTPUTS}}
            for s in result["strategies"]}
    Path(out).write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    print(json.dumps(snapshot, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
