"""Human-readable Markdown report of a v4 analysis (spec v4.0, section 2: the analysis package)."""
from app.science.equations import EQUATIONS
from app.services.run_v2 import OUTPUT_NAME

ROWS = ["et0", "etc_standard", "precipitation", "rainfed_eta", "rainfed_deficit", "rainfed_stress_days",
        "irrigated_net_irrigation"]


def _cell(summary: dict, key: str) -> str:
    s = summary[key]["spread"]
    return "unavailable" if s is None else f"{s['median']:g} ({s['p10']:g}–{s['p90']:g})"


def render(result: dict, analysis_id: str = "") -> str:
    loc, strategies = result["location"], result["strategies"]
    lines = [
        f"# Field Shift comparison {analysis_id}".rstrip(),
        "",
        f"Status: **{result['status']}** · Mode: {result['mode']} · State: {loc['state_name']} "
        f"(public location {loc['public_location']['lat']}, {loc['public_location']['lon']}) · "
        f"Seasons {result['period']['requested'][0]}–{result['period']['requested'][1]}",
        "",
        f"**Summary.** {result['summary']}",
        "",
        "## Strategies",
        "",
        "Median over simulated seasons, with the 10th–90th percentile range in brackets. "
        "Historical weather replay: not a forecast, not a probability of success, no yield or profit claim.",
        "",
        "| Output | Unit | Result type | " + " | ".join(f"{s['id']} {s['name']}" for s in strategies) + " |",
        "|---|---|---|" + "---|" * len(strategies),
    ]
    for key in ROWS:
        meta = strategies[0]["result"]["summary"][key] if strategies else None
        if meta:
            lines.append(f"| {OUTPUT_NAME[key]} | {meta['unit']} | {meta['result_type'].replace('_', ' ')} | "
                         + " | ".join(_cell(s["result"]["summary"], key) for s in strategies) + " |")
    lines += ["", "## Each strategy", ""]
    for s in strategies:
        r = s["result"]
        lines += [
            f"### {s['id']} {s['name']} ({s['role'].replace('_', ' ')})",
            "",
            f"- Why included: {s['why_included']}",
            f"- Planting date {s['planting']}; stages {s['parameters']['stages_days']} days; "
            f"Kc table {s['parameters']['kc_ini']}/{s['parameters']['kc_mid_table']}/{s['parameters']['kc_end_table']}; "
            f"p = {s['parameters']['p']}",
            f"- Root zone {r['root_depth_m']} m: TAW {r['taw_mm']} mm, RAW {r['raw_mm']} mm "
            f"(1/3–15 bar alternative TAW: {r['taw_fc_wp_mm']} mm)",
            f"- Seasons simulated: {r['seasons_simulated']}; excluded: "
            + (", ".join(f"{k} {v['count']} ({v['reason']})" for k, v in r["seasons_excluded"].items()) or "none"),
            "- Largest water-balance closure residual: "
            + ("not applicable" if r["max_closure_residual_mm"] is None else f"{r['max_closure_residual_mm']:.1e} mm"),
            f"- Rotation note ({s['rotation']['review_state']}): {s['rotation']['text']}",
            "",
        ]
    if result["rejected"]:
        lines += ["## Not evaluated", ""] + [f"- {r['crop']}: {r['reason']}" for r in result["rejected"]] + [""]
    lines += ["## What we know", "", "| Input | Status | Source | Effect |", "|---|---|---|---|"]
    lines += [f"| {i['name']} | {i['state']} | {i['source'] or '—'} | {i['effect']} |" for i in result["inputs"]]
    lines += ["", "## Limitations", ""] + [f"- {x}" for x in result["limitations"]]
    lines += ["", "## Equations", ""]
    lines += [f"- **{e}**: {EQUATIONS[e][0]} [{EQUATIONS[e][1]}]" for e in result["equations"]]
    w = result["provenance"]["weather"]
    lines += ["", "## Sources", "",
              f"- Weather: {w['provider']} {w['product']} {w['version']}, sources {', '.join(w['sources'])}, "
              f"{w['period'][0]} to {w['period'][1]}, retrieved {w['retrieved_utc']}, SHA-256 {w['content_sha256'][:16]}…",
              f"- {w['reference']}"]
    soil = result["provenance"].get("soil")
    if soil:
        lines.append(f"- Soil: {soil['product']}, map unit {soil['returned_support']['mukey']}, "
                     f"{soil['selection']}, retrieved {soil['retrieved_utc']}. {soil['reference']}")
    lines += [f"- FAO-56: {EQUATIONS['FAO56-Eq6'][2]}", f"- Runoff: {EQUATIONS['SCS-CN'][2]}",
              f"- Versions: {result['versions']}"]
    return "\n".join(lines) + "\n"
