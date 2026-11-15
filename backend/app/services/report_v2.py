"""Human-readable Markdown report of a v4 analysis (spec v4.0, section 2: the analysis package)."""
from app.science.equations import EQUATIONS
from app.services.run_v2 import OUTPUT_NAME
from html import escape

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
        "Relative water-gap score = each crop's median rain-fed deficit divided by the largest median deficit among these options, times 100. "
        "It compares only this analysis and is not a crop-failure probability or forecast. The historical season count below is separate.",
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
            f"- Relative water-gap score: {s.get('water_stress_exposure', {}).get('percentage', 'unavailable')}% "
            f"(median deficit {s.get('water_stress_exposure', {}).get('median_rainfed_deficit_mm', 'unavailable')} mm per season; "
            f"{s.get('water_stress_exposure', {}).get('seasons_affected', 0)}/"
            f"{s.get('water_stress_exposure', {}).get('seasons_assessed', 0)} valid seasons had a modeled stress day); "
            f"relative level {s.get('water_stress_exposure', {}).get('relative_level', 'unavailable')}; "
            f"main modeled factor: {s.get('water_stress_exposure', {}).get('primary_contributing_factor', 'unavailable')}",
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


def render_html(result: dict, analysis_id: str = "") -> str:
    """Print-friendly, complete analysis report suitable for the browser's Save as PDF."""
    esc = lambda value: escape(str(value if value is not None else "—"), quote=True)
    loc = result["location"]
    field = result.get("field_context") or {}
    strategies = result.get("strategies", [])
    goal_names = {"conserve_water": "Use less irrigation water", "reduce_drought_stress": "Compare drought stress",
                  "improve_soil_rotation": "Consider crop rotation"}
    summary_rows = []
    for key in ROWS:
        if not strategies:
            continue
        metric = strategies[0]["result"]["summary"].get(key)
        if not metric:
            continue
        values = "".join(f"<td>{esc(_cell(s['result']['summary'], key))}</td>" for s in strategies)
        summary_rows.append(f"<tr><th>{esc(OUTPUT_NAME[key])}<small>{esc(metric['unit'])} · median (p10–p90)</small></th>{values}</tr>")

    risk_cards = []
    for index, strategy in enumerate(strategies):
        risk = strategy.get("water_stress_exposure", {})
        pct = risk.get("percentage")
        width = max(0, min(100, float(pct or 0)))
        level = {"lower": "Lower than these options", "middle": "Between these options", "higher": "Higher than these options",
                 "similar": "Similar across options", "insufficient_data": "Not enough data"}.get(risk.get("relative_level"), "Not assessed")
        risk_cards.append(f"""<article class="risk-card" style="--crop-color:{['#2f6b3b','#b4532a','#3b5fa8'][index % 3]}">
          <div class="card-top"><span>OPTION {index + 1}</span><span class="level">{esc(level)}</span></div>
          <h3>{esc(strategy.get('name'))}</h3><p class="risk-number">{esc(f'{pct:g}%' if pct is not None else '—')}<small> relative water-gap score</small></p>
          <div class="risk-track"><i style="width:{width:g}%"></i></div>
          <p>Scaled against the largest median rain-fed deficit among these options. Historical seasons with any modeled stress day: {esc(risk.get('seasons_affected', 0))} of {esc(risk.get('seasons_assessed', 0))}.</p>
          <p><strong>Main modeled factor</strong><br>{esc(risk.get('primary_contributing_factor'))}</p>
        </article>""")

    detailed = []
    for strategy in strategies:
        r = strategy.get("result", {})
        summary = r.get("summary", {})
        metric_rows = "".join(
            f"<tr><th>{esc(OUTPUT_NAME.get(key, key))}</th><td>{esc(_cell(summary, key))}</td><td>{esc(summary.get(key, {}).get('unit'))}</td></tr>"
            for key in ROWS if key in summary)
        seasons = r.get("seasons", [])
        season_rows = "".join(
            "<tr>" + "".join(f"<td>{esc(season.get(key))}</td>" for key in
                ("year", "et0", "etc_standard", "precipitation", "rainfed_deficit", "rainfed_stress_days", "irrigated_net_irrigation")) + "</tr>"
            for season in seasons)
        params = strategy.get("parameters", {})
        sources = params.get("sources", {})
        source_rows = "".join(f"<li><strong>{esc(key)}:</strong> {esc(value)}</li>" for key, value in sources.items())
        detailed.append(f"""<section class="crop-detail">
          <h2>{esc(strategy.get('name'))} <small>{esc(strategy.get('role', '').replace('_', ' '))}</small></h2>
          <p>{esc(strategy.get('why_included'))} Planting date {esc(strategy.get('planting'))}; stages {esc(params.get('stages_days'))} days.</p>
          <div class="table-wrap"><table><thead><tr><th>Measure</th><th>Median (p10–p90)</th><th>Unit</th></tr></thead><tbody>{metric_rows}</tbody></table></div>
          <p><strong>Soil-water model:</strong> root zone {esc(r.get('root_depth_m'))} m; total available water {esc(r.get('taw_mm'))} mm; readily available water {esc(r.get('raw_mm'))} mm.</p>
          <p><strong>Season coverage:</strong> {esc(r.get('seasons_simulated'))} simulated; excluded {esc(r.get('seasons_excluded')) or 'none'}.</p>
          <p><strong>Rotation context:</strong> {esc(strategy.get('rotation', {}).get('text'))} <span class="muted">({esc(strategy.get('rotation', {}).get('review_state'))})</span></p>
          <h3>Crop assumptions and sources</h3><ul>{source_rows}</ul>
          <details open><summary>Season-by-season model output</summary><div class="table-wrap"><table><thead><tr><th>Year</th><th>ET₀<br>mm</th><th>Crop use<br>mm</th><th>Rain<br>mm</th><th>Water gap<br>mm</th><th>Stress days</th><th>Irrigation need<br>mm</th></tr></thead><tbody>{season_rows}</tbody></table></div></details>
        </section>""")

    profile = []
    labels = {"area_acres": "Field area (acres)", "soil_texture": "Farmer-reported soil texture", "drainage": "Farmer-reported drainage",
              "slope": "Farmer-reported slope", "water_source": "Water source", "notes": "Farmer notes"}
    for key, label in labels.items():
        if field.get(key) not in (None, "", "unknown"):
            profile.append(f"<tr><th>{esc(label)}</th><td>{esc(field[key])}</td></tr>")
    history = ", ".join(f"{h.get('year')}: {h.get('crop')}" for h in result.get("request", {}).get("history", [])) or "Not provided"
    soil = result.get("soil") or {}
    provenance = result.get("provenance", {})
    weather = provenance.get("weather", {})
    soil_prov = provenance.get("soil") or {}
    equations = "".join(f'<li><strong>{esc(e)}:</strong> {esc(EQUATIONS[e][0])} <span class="muted">[{esc(EQUATIONS[e][1])}]</span></li>'
                        for e in result.get("equations", []) if e in EQUATIONS)
    limitations = "".join(f"<li>{esc(item)}</li>" for item in result.get("limitations", []))
    crop_headers = "".join(f"<th>{esc(s.get('name'))}</th>" for s in strategies)
    field_name = field.get("name") or loc.get("state_name", "Field")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Field Shift report · {esc(field_name)}</title>
<style>
@page{{size:letter;margin:16mm 15mm 18mm;@bottom-right{{content:"Field Shift · Page " counter(page);font:8pt Arial;color:#728075}}}}
:root{{font-family:Arial,Helvetica,sans-serif;color:#1f3027;background:#fff;font-size:10pt;line-height:1.48}}*{{box-sizing:border-box}}body{{margin:0}}h1,h2,h3,p{{margin-top:0}}h1{{font-size:28pt;line-height:1.08;letter-spacing:-.5pt;margin:8pt 0}}h2{{font-size:16pt;border-bottom:1px solid #dbe4d9;padding-bottom:5pt;margin:20pt 0 8pt}}h3{{font-size:11pt;margin:13pt 0 5pt}}small{{display:block;font-size:8pt;color:#637469;font-weight:400}}.brand{{color:#2f6b3b;font-weight:bold;letter-spacing:2pt;font-size:9pt}}.hero{{padding:10pt 0 14pt;border-bottom:3pt solid #2f6b3b}}.meta{{display:flex;flex-wrap:wrap;gap:8pt 18pt;color:#536359;font-size:9pt}}.actions{{position:sticky;top:0;background:#fff;padding:8pt 0;border-bottom:1px solid #ddd}}button{{border:0;background:#2f6b3b;color:white;padding:8pt 12pt;border-radius:5pt;font-weight:bold}}.callout{{margin:14pt 0;padding:10pt 12pt;background:#f2f6ed;border-left:3pt solid #2f6b3b}}.risk-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:9pt}}.risk-card{{border:1px solid #dce4dc;border-top:4px solid var(--crop-color);border-radius:8px;padding:10pt;break-inside:avoid}}.card-top{{display:flex;justify-content:space-between;gap:5pt;color:#637469;font-size:7.5pt;font-weight:bold;text-transform:uppercase}}.level{{text-align:right}}.risk-card h3{{font-size:12pt;margin:8pt 0}}.risk-number{{font-size:23pt;font-weight:bold;margin:0}}.risk-number small{{display:inline;font-size:8pt;font-weight:normal}}.risk-track{{height:7px;border-radius:5px;background:#edf0eb;margin:6pt 0 8pt;overflow:hidden}}.risk-track i{{display:block;background:var(--crop-color);height:100%}}.risk-card p{{font-size:8.5pt;margin:7pt 0}}table{{width:100%;border-collapse:collapse;font-size:8pt;margin:8pt 0 14pt}}th,td{{border-bottom:1px solid #dce3dc;padding:5pt 6pt;text-align:left;vertical-align:top}}thead th{{background:#edf2e9;color:#31483a}}tbody tr:nth-child(even){{background:#fafbf9}}.summary td{{font-weight:bold}}.crop-detail{{break-before:page}}.crop-detail h2 small{{display:inline;margin-left:8pt}}.table-wrap{{overflow:visible}}.muted{{color:#637469}}.chip{{display:inline-block;padding:3pt 7pt;background:#eff4ea;border-radius:10pt;font-size:8pt}}ul{{padding-left:18pt}}li{{margin:3pt 0}}details summary{{font-weight:bold;margin:8pt 0}}.footer-note{{color:#637469;font-size:8pt;border-top:1px solid #dce3dc;padding-top:8pt;margin-top:18pt}}.no-print{{display:block}}@media print{{.no-print{{display:none}}.crop-detail{{break-before:page}}thead{{display:table-header-group}}tr{{break-inside:avoid}}a{{color:inherit;text-decoration:none}}}}
</style></head><body>
<div class="actions no-print"><button onclick="window.print()">Print or save as PDF</button> <span class="muted">In the print window, choose “Save as PDF”.</span></div>
<header class="hero"><div class="brand">FIELD SHIFT · FIELD ANALYSIS</div><h1>{esc(field_name)}</h1><p>Crop and water comparison from historical NASA weather and USDA soil information.</p>
<div class="meta"><span>{esc(loc.get('state_name'))}</span><span>Location {esc(loc.get('public_location',{}).get('lat'))}, {esc(loc.get('public_location',{}).get('lon'))}</span><span>Seasons {esc(result.get('period',{}).get('requested',["—","—"])[0])}–{esc(result.get('period',{}).get('requested',["—","—"])[1])}</span><span>Report ID {esc(analysis_id)}</span><span>Created {esc(result.get('generated'))}</span></div></header>
<div class="callout"><strong>How to interpret this report.</strong> The relative water-gap score divides each crop’s median rain-fed deficit by the largest median deficit among these options. It is a within-analysis comparison, not a probability of crop failure, yield, profit, or next-season conditions. The past-season count is shown separately. Crop parameters remain under review.</div>
<h2>Three crop options and relative water-gap scores</h2><div class="risk-grid">{''.join(risk_cards) or '<p>Risk comparison unavailable.</p>'}</div>
<h2>At-a-glance comparison</h2><p>Values are medians across the simulated seasons. Parentheses show the 10th–90th percentile range; units are named for each measure.</p><div class="table-wrap"><table class="summary"><thead><tr><th>Measure</th>{crop_headers}</tr></thead><tbody>{''.join(summary_rows)}</tbody></table></div>
<h2>Field profile</h2><table><tbody><tr><th>Field</th><td>{esc(field_name)}</td></tr><tr><th>State</th><td>{esc(loc.get('state_name'))}</td></tr><tr><th>Coordinates</th><td>{esc(loc.get('public_location',{}).get('lat'))}, {esc(loc.get('public_location',{}).get('lon'))} · regional grid support</td></tr><tr><th>Current crop</th><td>{esc(result.get('request',{}).get('current_practice') or 'Not identified')}</td></tr><tr><th>Irrigation</th><td>{esc(result.get('request',{}).get('irrigation', 'unknown'))}</td></tr><tr><th>Recent crop history</th><td>{esc(history)}</td></tr>{''.join(profile)}</tbody></table>
<p><strong>Mapped soil estimate:</strong> {esc(soil.get('label') or 'Unavailable')} {esc(' · hydrologic group ' + str(soil.get('hydrologic_group')) if soil.get('hydrologic_group') else '')}. Map-unit soil can vary within a field. Farmer-reported texture and notes are context only and do not replace the mapped soil input or a laboratory test.</p>
{''.join(detailed)}
<h2>Data sources and processing</h2><p><strong>NASA weather:</strong> {esc(weather.get('provider'))} {esc(weather.get('product'))} {esc(weather.get('version'))}; data period {esc(weather.get('period'))}; retrieved {esc(weather.get('retrieved_utc'))}.</p><p>{esc(weather.get('reference'))}</p><p><strong>USDA soil:</strong> {esc(soil_prov.get('product') or 'No soil record')} {esc(soil_prov.get('selection') or '')} {esc(soil_prov.get('reference') or '')}</p>
<h2>Equations and assumptions</h2><ul>{equations}</ul><p>Engine {esc(result.get('versions',{}).get('engine'))}; crop catalog {esc(result.get('versions',{}).get('crop_catalog'))}; boundary {esc(result.get('versions',{}).get('boundary'))}.</p>
<h2>Limitations</h2><ul>{limitations}</ul><div class="footer-note">Prepared by Field Shift. Historical scenarios are for exploration and discussion with a qualified local agronomist. This report is not a crop prescription, irrigation instruction, forecast, or guarantee of farm outcomes.</div>
</body></html>"""
