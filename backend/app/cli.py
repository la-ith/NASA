"""Run a v4 analysis without the web app (spec v4.0, Phase 2 gate: JSON and a readable report).

Examples, from the backend folder:
  python -m app.cli --site ks_hays --history maize_grain:2024,maize_grain:2025 --irrigation rain-fed
  python -m app.cli --live --lat 41.59 --lon -93.62 --goal reduce_drought_stress --out result.json --report report.md
--site uses the saved, validated demo records (offline). --live calls NASA POWER and USDA Soil Data Access.
"""
import argparse
import asyncio
import json
import sys
from datetime import date

import httpx

from app.adapters import AdapterError
from app.db.database import connect
from app.domain.crop_catalog import load_catalog
from app.geo.boundaries import state_at
from app.services import sources_v2
from app.services.report_v2 import render
from app.services.run_v2 import GOAL_ORDER, run_analysis


def parse_history(text: str) -> list[dict]:
    items = []
    for part in filter(None, (p.strip() for p in text.split(","))):
        crop, _, year = part.partition(":")
        items.append({"year": int(year), "crop": crop, "provenance": "farmer"})
    return items


async def main(args: argparse.Namespace) -> int:
    if args.site:
        lon, lat = sources_v2.DEMO_SITES[args.site]
        mode = "sample"
    else:
        lon, lat, mode = args.lon, args.lat, "live"
    state = state_at(lon, lat)
    if state is None:
        print("Outside the 50 U.S. states covered by this release.", file=sys.stderr)
        return 2
    request = {"lat": lat, "lon": lon, "start_year": args.start_year, "end_year": args.end_year, "goal": args.goal,
               "irrigation": args.irrigation, "history": parse_history(args.history or "")}
    db = connect(":memory:")
    try:
        async with httpx.AsyncClient() as client:
            weather = await sources_v2.weather(db, client, lon, lat, date(args.start_year, 1, 1),
                                               date(args.end_year, 12, 31), mode)
            soil = await sources_v2.soil(db, client, lon, lat, mode, None)
    except (AdapterError, sources_v2.SampleNotAvailable) as exc:
        print(f"{exc.code}: {exc}", file=sys.stderr)
        return 1
    result = run_analysis(request, state, weather, soil.soil, load_catalog(), mode)
    if soil.soil is None:
        result["limitations"].append(f"Soil: {soil.reason}.")
    report = render(result)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            f.write(report)
    if not args.out and not args.report:
        sys.stdout.reconfigure(encoding="utf-8")  # equations use Δ, γ and θ; Windows consoles default to cp1252
        print(report)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Field Shift v4 analysis")
    where = parser.add_mutually_exclusive_group(required=True)
    where.add_argument("--site", choices=sorted(sources_v2.DEMO_SITES))
    where.add_argument("--live", action="store_true")
    parser.add_argument("--lat", type=float)
    parser.add_argument("--lon", type=float)
    parser.add_argument("--start-year", type=int, default=2001)
    parser.add_argument("--end-year", type=int, default=2025)
    parser.add_argument("--goal", choices=list(GOAL_ORDER), default="conserve_water")
    parser.add_argument("--irrigation", choices=["rain-fed", "irrigated", "unknown"], default="unknown")
    parser.add_argument("--history", help="comma-separated crop:year, for example maize_grain:2024,soybean:2025")
    parser.add_argument("--out", help="write the JSON result here")
    parser.add_argument("--report", help="write the Markdown report here")
    parsed = parser.parse_args()
    if parsed.live and (parsed.lat is None or parsed.lon is None):
        parser.error("--live needs --lat and --lon")
    sys.exit(asyncio.run(main(parsed)))
