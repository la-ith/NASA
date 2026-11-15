// Soil layers: a cross-section of the field built only from values the API returns.
// Above ground: NASA POWER rainfall and modeled crop water use (analysis summary medians).
// Surface and 0–100 cm: NASA SMAP volumetric soil moisture, the latest valid daily value (context only).
// Root zone: FAO-56 root depth with total and readily available water (TAW / RAW) from the analysis.
// Soil column: the USDA SSURGO map-unit record. Depths are drawn to scale; no value is computed here.

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (n, digits = 0) => Number(n).toLocaleString("en-US", { maximumFractionDigits: digits });
const inch = (mm) => `${fmt(Number(mm) / 25.4, 1)} in`; // display conversion of a backend value
const has = (n) => n !== null && n !== undefined && n !== "" && Number.isFinite(Number(n));
const smapCache = new Map();

function cropLabel(strategy) {
  return strategy.crop === "maize_grain" ? "Corn" : strategy.name.replace(/\s*\(.*\)$/, "");
}

function median(strategy, key) {
  const value = strategy?.result?.summary?.[key]?.spread?.median;
  return has(value) ? Number(value) : null;
}

function restrictive(label) {
  if (!label) return null;
  if (/no restrictive layer/i.test(label)) return false;
  return /restrict|bedrock|duripan|fragipan|petrocalcic/i.test(label) ? true : null;
}

/** The section markup. Call wireSoilLayers(root, result) after it is in the DOM. */
export function soilLayersSection(result) {
  const strategies = (result.strategies || []).filter((s) => s.result);
  if (!result.soil || !strategies.length) {
    return `<section class="soil-section" aria-labelledby="soil-title"><header><div><p class="eyebrow">Under your field</p><h2 id="soil-title">Soil layers</h2><p>No mapped USDA soil record was available at this location, so the soil column and root-zone water storage can't be drawn. Check local soil information before relying on soil-related results.</p></div></header><div id="soil-smap" class="soil-layers"></div></section>`;
  }
  const first = strategies.find((s) => s.role === "current_practice") || strategies[0];
  return `<section class="soil-section" id="soil-section" aria-labelledby="soil-title">
    <header>
      <div><p class="eyebrow">Under your field · layer by layer</p><h2 id="soil-title">Soil layers and water</h2>
      <p>From the sky to the bottom of the mapped soil: where rain arrives, how deep each crop's roots reach, how much water that soil can hold, and NASA’s latest soil-moisture estimates (SMAP satellite and MERRA-2 model).</p></div>
      <div class="soil-crop-switch" role="group" aria-label="Show root zone for">${strategies.map((s) => `<button type="button" data-soil-crop="${esc(s.id)}" aria-pressed="${s === first}">${esc(cropLabel(s))}</button>`).join("")}</div>
    </header>
    <div class="soil-body">
      <figure class="soil-figure" id="soil-figure"></figure>
      <ol class="soil-layers" id="soil-list"></ol>
    </div>
    <p class="soil-note">Depths are drawn to scale. SMAP moisture (m³/m³) is a model-assisted satellite estimate for a ~9 km cell; MERRA-2 wetness (0–1) is a separate NASA reanalysis estimate for a ~50 km cell. Neither is a sample from your field, they are shown side by side and never merged, and neither changes the water-balance results above. Root depth and water-holding values come from FAO-56 crop parameters and the mapped soil record.</p>
  </section>`;
}

function drawFigure(result, strategy, smap) {
  const soil = result.soil;
  const rootCm = has(strategy.result.root_depth_m) ? Number(strategy.result.root_depth_m) * 100 : null;
  const soilCm = has(soil.depth_cm) ? Number(soil.depth_cm) : null;
  const deepest = Math.max(soilCm || 0, rootCm || 0, 100);
  const W = 640, top = 96, bottom = 404, H = 430;
  const y = (cm) => top + (cm / deepest) * (bottom - top);
  const rootY = rootCm ? y(rootCm) : null;
  const soilY = soilCm ? y(soilCm) : bottom;
  const surfaceY = Math.max(y(5), top + 12);
  const rain = median(strategy, "precipitation");
  const use = median(strategy, "etc_standard");
  const taw = strategy.result.taw_mm, raw = strategy.result.raw_mm;
  const rawShare = has(taw) && has(raw) && Number(taw) > 0 ? Math.min(1, Number(raw) / Number(taw)) : null;
  const restrict = restrictive(soil.label);
  const ticks = [0, 50, 100, 150, 200, 250, 300].filter((cm) => cm <= deepest);
  const roots = rootY ? [-26, -14, -4, 6, 16, 28].map((dx, i) => {
    const len = (rootY - top) * (0.55 + (i % 3) * 0.18);
    return `<path d="M250 ${top} C ${250 + dx * 0.4} ${top + len * 0.35}, ${250 + dx * 1.6} ${top + len * 0.7}, ${250 + dx * 2.2} ${top + len}" />`;
  }).join("") : "";
  const tankTop = top + 6, tankBottom = rootY ? rootY - 6 : top + 60;
  const tankH = Math.max(24, tankBottom - tankTop);
  const smapSurface = smap?.surface, smapRoot = smap?.root;
  const wetSurface = smap?.merra2?.surface, wetRoot = smap?.merra2?.root;

  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-labelledby="soil-svg-title soil-svg-desc">
    <title id="soil-svg-title">Soil cross-section for ${esc(cropLabel(strategy))}</title>
    <desc id="soil-svg-desc">Mapped soil ${soilCm ? `${fmt(soilCm)} cm deep` : "depth not recorded"}; root zone ${rootCm ? `${fmt(rootCm)} cm` : "not available"}; total available water ${has(taw) ? `${fmt(taw, 1)} mm` : "not available"}.</desc>
    <defs>
      <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#cfe2ef"/><stop offset="1" stop-color="#eef3e6"/></linearGradient>
      <linearGradient id="rootzone" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#9c7650"/><stop offset="1" stop-color="#7c5a3c"/></linearGradient>
      <linearGradient id="subsoil" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#6c4f37"/><stop offset="1" stop-color="#4c3829"/></linearGradient>
      <pattern id="grain" width="9" height="9" patternUnits="userSpaceOnUse"><circle cx="2" cy="3" r=".9" fill="rgb(255 255 255 / .16)"/><circle cx="7" cy="7" r=".7" fill="rgb(0 0 0 / .12)"/></pattern>
      <pattern id="hatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><path d="M0 0v8" stroke="#2b2018" stroke-width="3"/></pattern>
    </defs>
    <rect width="${W}" height="${top}" fill="url(#sky)"/>
    ${rain !== null ? `<g stroke="#3b78a8" stroke-width="2" stroke-linecap="round"><path d="M70 18v22M86 26v22M102 14v22M118 24v22"/></g><text x="64" y="70" class="soil-svg-label dark">Rain ${inch(rain)} · ${fmt(rain)} mm</text><text x="64" y="84" class="soil-svg-small" style="fill:#55625a">median per season · NASA POWER</text>` : ""}
    ${use !== null ? `<g fill="none" stroke="#b07a2a" stroke-width="2" stroke-linecap="round"><path d="M400 58c-6-8 6-12 0-20s6-12 0-20M416 58c-6-8 6-12 0-20s6-12 0-20"/></g><text x="436" y="44" class="soil-svg-label dark">Crop water use ${inch(use)}</text><text x="436" y="58" class="soil-svg-small" style="fill:#55625a">median per season · FAO-56 model</text>` : ""}
    <g fill="none" stroke="#2f6a4f" stroke-width="3" stroke-linecap="round"><path d="M250 ${top} V ${top - 46}"/><path d="M250 ${top - 18}c-14-4-22-14-24-26 13 2 22 12 24 26zM250 ${top - 30}c14-4 22-14 24-26-13 2-22 12-24 26z" fill="#4f8a5e"/></g>
    <rect x="0" y="${top}" width="${W}" height="${soilY - top}" fill="url(#subsoil)"/>
    ${rootY ? `<rect x="0" y="${top}" width="${W}" height="${rootY - top}" fill="url(#rootzone)"/>` : ""}
    <rect x="0" y="${top}" width="${W}" height="${surfaceY - top}" fill="#b98f62"/>
    <rect x="0" y="${top}" width="${W}" height="${soilY - top}" fill="url(#grain)"/>
    ${soilY < bottom ? `<rect x="0" y="${soilY}" width="${W}" height="${bottom - soilY}" fill="#3a2c22"/>` : ""}
    ${restrict ? `<rect x="0" y="${soilY - 6}" width="${W}" height="10" fill="url(#hatch)" opacity=".7"/>` : ""}
    <g fill="none" stroke="#e9f0d5" stroke-width="1.6" stroke-linecap="round" opacity=".85">${roots}</g>
    ${rootY ? `<path d="M0 ${rootY}H${W}" stroke="#f4f1e6" stroke-width="1.5" stroke-dasharray="6 5"/><text x="300" y="${rootY - 8}" class="soil-svg-label">Roots reach ${fmt(rootCm / 2.54)} in (${fmt(rootCm)} cm)</text>` : ""}
    <path d="M0 ${y(100)}H${W}" stroke="#9cc3e0" stroke-width="1.2" stroke-dasharray="2 4" opacity=".9"/>
    <text x="300" y="${y(100) + 15}" class="soil-svg-small">Moisture root-zone layer ends · 100 cm${has(smapRoot?.value) ? ` · SMAP ${fmt(smapRoot.value * 100, 0)}% moisture` : ""}${has(wetRoot?.value) ? ` · MERRA-2 wetness ${fmt(wetRoot.value, 2)}` : ""}</text>
    <text x="300" y="${surfaceY - 2 > top + 8 ? surfaceY - 2 : top + 11}" class="soil-svg-small">Surface 0–5 cm${has(smapSurface?.value) ? ` · SMAP ${fmt(smapSurface.value * 100, 0)}% moisture` : ""}${has(wetSurface?.value) ? ` · MERRA-2 wetness ${fmt(wetSurface.value, 2)}` : ""}</text>
    <text x="300" y="${Math.min(soilY - 10, bottom - 8)}" class="soil-svg-label">${soilCm ? `Mapped soil ends · ${fmt(soilCm)} cm` : "Soil depth not recorded"}${restrict ? " · restrictive layer" : ""}</text>
    ${has(taw) && rootY ? `<g>
      <rect x="566" y="${tankTop}" width="46" height="${tankH}" rx="10" fill="rgb(255 255 255 / .22)" stroke="rgb(255 255 255 / .7)"/>
      <rect x="569" y="${tankTop + 3}" width="40" height="${tankH - 6}" rx="8" fill="#cfe1ee" opacity=".55"/>
      ${rawShare !== null ? `<rect x="569" y="${tankTop + 3}" width="40" height="${(tankH - 6) * rawShare}" rx="8" fill="#3b78a8"/>` : ""}
      <text x="589" y="${tankBottom + 16}" text-anchor="middle" class="soil-svg-label">${inch(taw)}</text>
    </g>` : ""}
    <g class="soil-svg-small">${ticks.map((cm) => `<path d="M0 ${y(cm)}h10" stroke="rgb(255 255 255 / .7)"/><text x="14" y="${y(cm) + 4}">${cm} cm</text>`).join("")}</g>
    <rect y="${bottom}" width="${W}" height="${H - bottom}" fill="#f8f7f2"/>
    <g font-size="10" fill="#55625a" font-family="DM Sans, sans-serif"><rect x="12" y="${bottom + 9}" width="10" height="10" rx="2" fill="#3b78a8"/><text x="27" y="${bottom + 18}">Easy for the crop to use</text><rect x="210" y="${bottom + 9}" width="10" height="10" rx="2" fill="#cfe1ee"/><text x="225" y="${bottom + 18}">Harder to use · crop starts to struggle</text></g>
  </svg><figcaption>${esc(cropLabel(strategy))} · drawn to scale from 0 to ${fmt(deepest)} cm</figcaption>`;
}

function layerList(result, strategy, smap) {
  const soil = result.soil;
  const r = strategy.result;
  const rain = median(strategy, "precipitation"), et0 = median(strategy, "et0"), use = median(strategy, "etc_standard");
  const smapLine = (entry, what) => {
    if (smap === undefined) return `<p>Loading the latest NASA SMAP estimate…</p>`;
    if (!entry || !has(entry.value)) return `<p>${esc(what)}: <span class="value">Not available</span> · ${smap?.error ? esc(smap.error) : "NASA POWER lists SMAP soil moisture but currently returns no values for it"}. You can still view SMAP imagery on the map: open “Map data” and choose a NASA soil-moisture layer.</p>`;
    return `<p>${esc(what)}: about <span class="value">${fmt(entry.value * 100, 0)}% of the soil is water</span> on ${esc(entry.date)} (${fmt(entry.value, 3)} m³/m³).</p>`;
  };
  const wetLine = (entry) => {
    if (smap === undefined) return `<p>Loading the latest MERRA-2 estimate…</p>`;
    if (!entry || !has(entry.value)) return `<p>Model soil wetness: <span class="value">Not available</span>${smap?.merra2?.error ? ` · ${esc(smap.merra2.error)}` : " for the last 120 days"}.</p>`;
    return `<p>How wet the soil was on ${esc(entry.date)}: <span class="value">${fmt(entry.value * 100, 0)}% of fully soaked</span> (0% is bone dry). A NASA model estimate, not a satellite reading.</p>`;
  };
  return `
    <li class="soil-layer"><i style="background:linear-gradient(#cfe2ef,#eef3e6)"></i><div><h3>Above the field <span>season</span></h3>
      <p>In a typical past season, rain brought <span class="value">${rain !== null ? `${inch(rain)} (${fmt(rain)} mm)` : "an unknown amount"}</span> and ${esc(cropLabel(strategy))} used about <span class="value">${use !== null ? `${inch(use)} (${fmt(use)} mm)` : "an unknown amount"}</span> of water.</p><p class="hint">Weather demand (reference ET₀): ${et0 !== null ? `${inch(et0)}` : "not available"}.</p>
      <span class="source-tag nasa">NASA POWER</span> <span class="source-tag model">FAO-56</span></div></li>
    <li class="soil-layer"><i style="background:#b98f62"></i><div><h3>Surface <span>0–5 cm</span></h3>${smapLine(smap?.surface, "Recent surface moisture")}<span class="source-tag nasa">NASA SMAP L4 · SFMC</span>${wetLine(smap?.merra2?.surface)}<span class="source-tag model">NASA MERRA-2 · GWETTOP</span></div></li>
    <li class="soil-layer"><i style="background:#8f6844"></i><div><h3>${esc(cropLabel(strategy))} root zone <span>${has(r.root_depth_m) ? `0–${fmt(r.root_depth_m * 100)} cm` : "depth not available"}</span></h3>
      <p>Within the roots’ reach, the soil holds about <span class="value">${has(r.taw_mm) ? `${inch(r.taw_mm)} (${fmt(r.taw_mm, 0)} mm)` : "an unknown amount"}</span> of water the crop can use. Once about <span class="value">${has(r.raw_mm) ? inch(r.raw_mm) : "—"}</span> of it is used up, the crop starts to struggle.</p><p class="hint">Technical names: total available water (TAW) and readily available water (RAW).</p>
      <span class="source-tag usda">USDA SSURGO</span> <span class="source-tag model">FAO-56 Eqs. 82–83</span></div></li>
    <li class="soil-layer"><i style="background:#9cc3e0"></i><div><h3>Satellite root-zone layer <span>0–100 cm</span></h3>${smapLine(smap?.root, "Recent root-zone moisture")}<span class="source-tag nasa">NASA SMAP L4 · RZMC</span>${wetLine(smap?.merra2?.root)}<span class="source-tag model">NASA MERRA-2 · GWETROOT</span></div></li>
    <li class="soil-layer"><i style="background:#5b4330"></i><div><h3>Mapped soil column <span>${has(soil.depth_cm) ? `0–${fmt(soil.depth_cm)} cm` : "depth not recorded"}</span></h3>
      <p>${esc(soil.label)}.</p><p>How fast rain soaks in: <span class="value">group ${esc(soil.hydrologic_group || "—")}</span> (A soaks in fastest, D slowest). A mapped estimate, not a field test.</p><p class="hint">Runoff curve number ${esc(soil.curve_number ?? "—")}.</p>
      <span class="source-tag usda">USDA SSURGO</span></div></li>`;
}

// The latest valid daily value of each series. A lookup, not a calculation.
function latest(series) {
  const days = Object.keys(series || {}).filter((d) => has(series[d])).sort();
  const d = days.at(-1);
  return d ? { value: Number(series[d]), date: `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}` } : null;
}

function queryProduct(product, lat, lon, daysBack) {
  const day = (offset) => new Date(Date.now() - offset * 86400000).toISOString().slice(0, 10);
  return fetch(`/api/v2/products/${product}/query`, {
    method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ lat, lon, start: day(daysBack), end: day(1) }),
  }).then(async (response) => {
    const body = await response.json().catch(() => ({}));
    if (!response.ok) return { error: response.status === 502 ? "the NASA service did not respond" : "not available for this request" };
    return { values: body.values || {} };
  }).catch(() => ({ error: "the request could not be completed" }));
}

// SMAP (satellite, m³/m³) and MERRA-2 (model, 0–1 wetness) are separate products and are never merged.
async function loadSmap(lat, lon) {
  const key = `${lat},${lon}`;
  if (smapCache.has(key)) return smapCache.get(key);
  const request = Promise.all([queryProduct("smap", lat, lon, 45), queryProduct("merra2_soil_wetness", lat, lon, 120)])
    .then(([smap, wet]) => ({
      surface: latest(smap.values?.SFMC), root: latest(smap.values?.RZMC), error: smap.error,
      merra2: { surface: latest(wet.values?.GWETTOP), root: latest(wet.values?.GWETROOT), error: wet.error },
    }));
  smapCache.set(key, request);
  return request;
}

export function wireSoilLayers(root, result) {
  const section = root.querySelector("#soil-section");
  const strategies = (result.strategies || []).filter((s) => s.result);
  const point = result.location?.public_location;
  if (!section || !result.soil || !strategies.length) return;
  let active = strategies.find((s) => s.role === "current_practice") || strategies[0];
  let smap; // undefined while loading
  const figure = section.querySelector("#soil-figure"), list = section.querySelector("#soil-list");
  const paint = () => { figure.innerHTML = drawFigure(result, active, smap); list.innerHTML = layerList(result, active, smap); };
  section.querySelectorAll("[data-soil-crop]").forEach((button) => button.onclick = () => {
    active = strategies.find((s) => s.id === button.dataset.soilCrop) || active;
    section.querySelectorAll("[data-soil-crop]").forEach((b) => b.setAttribute("aria-pressed", String(b === button)));
    paint();
  });
  paint();
  if (point && has(point.lat) && has(point.lon)) {
    loadSmap(Number(point.lat), Number(point.lon)).then((value) => { smap = value; if (section.isConnected) paint(); });
  } else { smap = { error: "no location" }; paint(); }
}
