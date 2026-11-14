// Field Shift U.S. web app (spec v4.0, section 19). Every number shown comes from the /api/v2 analysis snapshot;
// the browser calculates nothing scientific. The Hebron regression app lives at /v1/.
const API = "/api/v2";
const POLL_MS = 600;
const DEMO_SITES = {
  ks_hays: { name: "Hays, Kansas (semi-arid, rain-fed)", lat: 38.85, lon: -99.33 },
  ia_ames: { name: "Ames, Iowa (humid Corn Belt)", lat: 42.03, lon: -93.62 },
};
const VIEWS = { lower48: [[-125, 24], [-66.5, 49.5]], alaska: [[-180, 51], [-129, 71.5]], hawaii: [[-160.6, 18.8], [-154.7, 22.3]] };
const GOALS = {
  conserve_water: "Conserve water (net irrigation need first)",
  reduce_drought_stress: "Reduce drought stress (rain-fed deficit first)",
  improve_soil_rotation: "Improve soil and rotation (rotation notes first)",
};
const OUTPUTS = {
  et0: "Reference ET0", etc_standard: "Crop water demand ETc", precipitation: "Season rainfall",
  rainfed_eta: "Rain-fed actual ET", rainfed_deficit: "Rain-fed water deficit",
  rainfed_stress_days: "Rain-fed stress days", irrigated_net_irrigation: "Net irrigation requirement",
};
const NOTICE = "Field Shift compares strategies under past weather using the sources shown. Regional grid data may not " +
  "represent your exact field, past seasons do not predict the next one, and nothing here estimates yield or profit. " +
  "Review choices with local agricultural expertise.";
const SERIES_COLORS = ["#2f6b3b", "#b4532a", "#3b5fa8"];
const BLANK_STYLE = { version: 8, sources: {}, layers: [{ id: "background", type: "background", paint: { "background-color": "#eef1ea" } }] };

const panel = document.getElementById("panel");
const mapStatus = document.getElementById("map-status");
document.getElementById("notice").textContent = NOTICE;
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const store = {
  get(k, d) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* storage unavailable */ } },
};

let form = store.get("fs2-form", null) || {
  lat: "", lon: "", mode: "live", goal: "conserve_water", irrigation: "unknown",
  history: [{ year: 2024, crop: "unknown" }, { year: 2025, crop: "unknown" }],
};
let coverage = null;
let catalog = null;
let equations = null;
let current = store.get("fs2-result", null);
let runToken = 0; // a newer run makes older responses stale (spec 19.4)
const saveForm = () => store.set("fs2-form", form);

async function getJSON(url, options) {
  const response = await fetch(url, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw Object.assign(new Error(body?.error?.message || `HTTP ${response.status}`), { body, status: response.status });
  return body;
}

// ---------- map ----------
let map = null;
let marker = null;
function initMap() {
  if (!window.maplibregl) { mapStatus.textContent = "The map library did not load; type coordinates in the form instead."; return; }
  map = new maplibregl.Map({
    container: "map", style: "https://tiles.openfreemap.org/styles/positron",
    bounds: VIEWS.lower48, fitBoundsOptions: { padding: 20 }, attributionControl: { compact: true },
  });
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
  let fallback = false;
  map.on("error", (e) => {
    const message = String(e?.error?.message || "");
    if (!fallback && !map.isStyleLoaded()) { // basemap style unreachable: keep a plain map with the state outlines
      fallback = true;
      map.setStyle(BLANK_STYLE);
      mapStatus.textContent = "Basemap unavailable; showing state outlines only. Typed coordinates still work.";
    } else if (/tile/i.test(message)) {
      mapStatus.textContent = "Some basemap tiles did not load; state outlines and typed coordinates still work.";
    }
  });
  map.on("style.load", () => { // runs for the basemap and again for the fallback style
    if (map.getSource("states")) return;
    map.addSource("states", { type: "geojson", data: `${API}/boundaries`, attribution: "U.S. Census Bureau 2023 cartographic boundaries" });
    map.addLayer({ id: "states-fill", type: "fill", source: "states", paint: { "fill-color": "#2f6b3b", "fill-opacity": 0.06 } });
    map.addLayer({ id: "states-line", type: "line", source: "states", paint: { "line-color": "#2f6b3b", "line-width": 0.8 } });
  });
  if (form.lat !== "" && form.lon !== "") placeMarker(Number(form.lat), Number(form.lon));
  map.on("click", (e) => {
    const { lat, lng } = e.lngLat.wrap(); // wrap keeps longitudes in -180..180 across the antimeridian
    setPoint(Number(lat.toFixed(4)), Number(lng.toFixed(4)), "live");
  });
  document.querySelectorAll(".map-shortcuts button").forEach((b) => {
    b.onclick = () => map.fitBounds(VIEWS[b.dataset.view], { padding: 20 });
  });
}
function placeMarker(lat, lon) {
  if (!map) return;
  if (!marker) marker = new maplibregl.Marker({ color: "#b4532a" });
  marker.setLngLat([lon, lat]).addTo(map);
}

async function setPoint(lat, lon, mode) {
  form.lat = lat; form.lon = lon; form.mode = mode; saveForm();
  placeMarker(lat, lon);
  coverage = { loading: true };
  renderForm();
  try {
    coverage = await getJSON(`${API}/coverage`, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lat, lon, mode }) });
  } catch (err) {
    coverage = { error: err.message };
  }
  renderForm();
}

// ---------- form ----------
function coverageHtml() {
  if (!coverage) return `<p class="muted small">Click the map, type coordinates, or pick a demo site.</p>`;
  if (coverage.loading) return `<p class="muted small" aria-live="polite">Checking data coverage…</p>`;
  if (coverage.error) return `<div class="errors">${esc(coverage.error)}</div>`;
  if (!coverage.in_scope) return `<div class="errors">${esc(coverage.reason)}</div>`;
  return `<p><strong>${esc(coverage.state.name)}</strong>${coverage.demo_site ? " · demo site (saved sample available)" : ""}</p>
    <div class="chips">${Object.entries(coverage.products).map(([k, v]) =>
      `<span class="chip ${esc(v.status)}" title="${esc(v.reason)}">${esc(k)}: ${esc(v.status.replace("_", " "))}</span>`).join("")}</div>
    ${coverage.products.ssurgo?.label ? `<p class="small muted">Soil: ${esc(coverage.products.ssurgo.label)}</p>` : ""}`;
}

function cropOptions(selected) {
  const crops = catalog?.crops || [];
  return [["unknown", "Unknown"], ...crops.map((c) => [c.id, c.name]), ["other", "Other crop"]]
    .map(([v, t]) => `<option value="${esc(v)}"${v === selected ? " selected" : ""}>${esc(t)}</option>`).join("");
}

function renderForm(errors = []) {
  const inScope = coverage && coverage.in_scope;
  const demo = coverage?.demo_site;
  panel.innerHTML = `
    <h1>Compare crop strategies for a U.S. field</h1>
    <p class="small">Each strategy is run through 25 past seasons of real NASA weather with FAO-56 water equations and
      USDA soil data. The result is a historical replay, not a forecast.</p>
    <div class="actions">${Object.entries(DEMO_SITES).map(([k, s]) => `<button data-demo="${k}">${esc(s.name)}</button>`).join("")}</div>
    <form id="form" novalidate>
      <fieldset><legend>Location</legend>
        <div class="row">
          <div><label for="lat">Latitude (°N)</label><input id="lat" type="number" step="0.0001" inputmode="decimal" value="${esc(form.lat)}"></div>
          <div><label for="lon">Longitude (°E, negative = west)</label><input id="lon" type="number" step="0.0001" inputmode="decimal" value="${esc(form.lon)}"></div>
        </div>
        <div class="actions"><button type="button" id="check">Check this location</button></div>
        ${coverageHtml()}
      </fieldset>
      <fieldset><legend>Recent crops</legend>
        ${form.history.map((h, i) => `<label for="h${i}">Season ${h.year}</label><select id="h${i}" data-i="${i}">${cropOptions(h.crop)}</select>`).join("")}
        <p class="hint">The last season's crop becomes current practice when it is in the catalog. Unknown stays unknown.</p>
      </fieldset>
      <fieldset><legend>Irrigation</legend>
        ${["rain-fed", "irrigated", "unknown"].map((v) => `<label class="choice"><input type="radio" name="irr" value="${v}"${form.irrigation === v ? " checked" : ""}> ${v}</label>`).join("")}
      </fieldset>
      <label for="goal">Goal <span class="hint">(orders the results; never changes a number)</span></label>
      <select id="goal">${Object.entries(GOALS).map(([v, t]) => `<option value="${v}"${form.goal === v ? " selected" : ""}>${esc(t)}</option>`).join("")}</select>
      <fieldset><legend>Data</legend>
        <label class="choice"><input type="radio" name="mode" value="live"${form.mode === "live" ? " checked" : ""}> Live NASA POWER and USDA Soil Data Access</label>
        <label class="choice"><input type="radio" name="mode" value="sample"${form.mode === "sample" ? " checked" : ""}${demo ? "" : " disabled"}> Saved sample records (demo sites only)</label>
      </fieldset>
      ${errors.length ? `<div class="errors"><ul>${errors.map((e) => `<li>${esc(e)}</li>`).join("")}</ul></div>` : ""}
      <div class="actions"><button class="primary" type="submit"${inScope ? "" : " disabled"}>Run analysis</button>
        ${current ? `<button type="button" id="last">Open last result</button>` : ""}</div>
    </form>`;
  panel.querySelectorAll("[data-demo]").forEach((b) => {
    b.onclick = () => { const s = DEMO_SITES[b.dataset.demo]; map?.flyTo({ center: [s.lon, s.lat], zoom: 6 }); setPoint(s.lat, s.lon, "sample"); };
  });
  document.getElementById("check").onclick = () => {
    const lat = Number(document.getElementById("lat").value), lon = Number(document.getElementById("lon").value);
    if (Number.isFinite(lat) && Number.isFinite(lon) && document.getElementById("lat").value !== "") setPoint(lat, lon, "live");
  };
  panel.querySelectorAll("select[data-i]").forEach((s) => { s.onchange = () => { form.history[Number(s.dataset.i)].crop = s.value; saveForm(); }; });
  panel.querySelectorAll('input[name="irr"]').forEach((r) => { r.onchange = () => { form.irrigation = r.value; saveForm(); }; });
  panel.querySelectorAll('input[name="mode"]').forEach((r) => { r.onchange = () => { form.mode = r.value; saveForm(); }; });
  document.getElementById("goal").onchange = (e) => { form.goal = e.target.value; saveForm(); };
  document.getElementById("last")?.addEventListener("click", () => renderResult(current));
  document.getElementById("form").onsubmit = (e) => { e.preventDefault(); run(); };
}

// ---------- run: async job with stage display (spec 21.2) ----------
async function run() {
  const token = ++runToken;
  const body = {
    mode: form.mode, lat: Number(form.lat), lon: Number(form.lon), goal: form.goal, irrigation: form.irrigation,
    history: form.history.map((h) => ({ year: h.year, crop: h.crop, provenance: "farmer" })), // unknown stays explicit
  };
  panel.innerHTML = `<h1>Running the analysis</h1><p aria-live="polite" id="stage">Starting…</p>
    <p class="small muted">Weather, soil, then 25 seasons × 3 strategies × 2 scenarios of the daily water balance.</p>`;
  try {
    const job = await getJSON(`${API}/analyses`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    for (;;) {
      if (token !== runToken) return; // a newer run started
      const state = await getJSON(job.status_url);
      const stage = document.getElementById("stage");
      if (stage) stage.textContent = `${state.state}: ${String(state.stage).replace("_", " ")}`;
      if (state.state === "succeeded") {
        const result = await getJSON(state.analysis_url);
        if (token !== runToken) return;
        current = result; store.set("fs2-result", result);
        renderResult(result);
        return;
      }
      if (state.state === "failed") { renderFailure(state.error); return; }
      await new Promise((r) => setTimeout(r, POLL_MS));
    }
  } catch (err) {
    if (err.body?.error?.code === "invalid_input") renderForm((err.body.error.fields || []).map((f) => String(f.msg).replace(/^Value error, /, "")));
    else renderFailure(err.body?.error || { code: navigator.onLine ? "network" : "offline", message: err.message, retryable: true });
  }
}

function renderFailure(error) {
  const titles = { provider_error: "A data provider did not respond", data_integrity: "Data error: the response did not match the request",
    sample_not_available: "No saved sample for this location", outside_scope: "Outside the U.S. release", offline: "You are offline" };
  panel.innerHTML = `<h1>${esc(titles[error.code] || "The analysis could not finish")}</h1>
    <div class="errors"><p>${esc(error.message || "")}</p><p class="small">Stage: ${esc(error.stage || "—")}</p></div>
    <div class="actions"><button id="back">Back to the form</button>${error.retryable ? `<button class="primary" id="retry">Retry</button>` : ""}</div>`;
  document.getElementById("back").onclick = () => renderForm();
  document.getElementById("retry")?.addEventListener("click", run);
}

// ---------- results ----------
function cell(summary, key) {
  const s = summary[key].spread;
  return s ? `${s.median}<span class="range">${s.p10}–${s.p90}</span>` : `<span class="muted">unavailable</span>`;
}

function deficitChart(r) {
  const series = r.strategies.map((s) => s.result.seasons.filter((x) => x.rainfed_deficit != null).map((x) => [x.year, x.rainfed_deficit]));
  const points = series.flat();
  if (!points.length) return "";
  const years = points.map((p) => p[0]), maxY = Math.max(...points.map((p) => p[1]), 1) * 1.1;
  const [y0, y1] = [Math.min(...years), Math.max(...years)];
  const W = 640, H = 220, L = 44, B = 26, T = 8;
  const x = (yr) => L + ((yr - y0) / Math.max(y1 - y0, 1)) * (W - L - 10), y = (v) => T + (H - B - T) * (1 - v / maxY);
  const step = maxY > 400 ? 100 : 50;
  const grid = Array.from({ length: Math.floor(maxY / step) + 1 }, (_, i) => i * step).map((v) =>
    `<line x1="${L}" x2="${W - 10}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)"/><text x="${L - 6}" y="${y(v) + 4}" font-size="10" text-anchor="end" fill="currentColor">${v}</text>`).join("");
  const xLabels = years.filter((yr, i, a) => a.indexOf(yr) === i && (yr - y0) % 5 === 0)
    .map((yr) => `<text x="${x(yr)}" y="${H - 8}" font-size="10" text-anchor="middle" fill="currentColor">${yr}</text>`).join("");
  const lines = series.map((pts, i) => `<polyline fill="none" stroke="${SERIES_COLORS[i]}" stroke-width="2" points="${pts.map(([a, b]) => `${x(a)},${y(b)}`).join(" ")}"/>`).join("");
  return `<figure class="chart"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Rain-fed water deficit per past season for each strategy, mm. The seasons table lists every value.">${grid}${lines}${xLabels}</svg>
    <figcaption class="legend">${r.strategies.map((s, i) => `<span><span class="swatch" style="background:${SERIES_COLORS[i]}"></span>${esc(s.name)}</span>`).join("")}
    <span>Rain-fed water deficit, mm per season</span></figcaption></figure>`;
}

async function renderResult(r) {
  if (!equations) equations = await getJSON(`${API}/equations`).catch(() => ({}));
  const order = r.output_order.filter((o) => o !== "rotation");
  const rows = [...order, ...Object.keys(OUTPUTS).filter((k) => !order.includes(k))];
  const soilLine = r.soil ? `${esc(r.soil.label)} · curve number ${r.soil.curve_number}` : "No soil data: water balance not run";
  const w = r.provenance.weather;
  panel.innerHTML = `
    <h1>Comparison: ${esc(r.location.state_name)}</h1>
    ${r.mode === "sample" ? `<div class="banner">Sample mode: saved NASA and USDA records, not a live retrieval.</div>` : ""}
    <div class="banner">Crop parameters and rotation notes are draft and not reviewed by an agronomist.</div>
    <p><strong>${esc(r.summary)}</strong></p>
    <p class="small muted">Status ${esc(r.status)} · seasons ${r.period.requested[0]}–${r.period.requested[1]} · public location ${r.location.public_location.lat}, ${r.location.public_location.lon} · analysis ${esc(r.analysis_id || "")}</p>
    <p class="small">Soil: ${soilLine}</p>
    <h2>Strategies</h2>
    <div class="table-wrap"><table>
      <thead><tr><th>Output (median, 10th–90th pct.)</th>${r.strategies.map((s) => `<th>${esc(s.name)}<br><span class="small muted">${esc(s.role.replace("_", " "))}</span></th>`).join("")}</tr></thead>
      <tbody>${rows.map((k) => `<tr><td>${OUTPUTS[k]}<span class="range">${esc(r.strategies[0].result.summary[k].unit)} · ${esc(r.strategies[0].result.summary[k].result_type.replace("_", " "))}</span></td>
        ${r.strategies.map((s) => `<td class="num">${cell(s.result.summary, k)}</td>`).join("")}</tr>`).join("")}</tbody>
    </table></div>
    ${deficitChart(r)}
    ${r.strategies.map((s) => `<div class="strategy${s.role === "current_practice" ? " current" : ""}">
      <h3>${esc(s.id)} ${esc(s.name)} <span class="small muted">${esc(s.role.replace("_", " "))}</span></h3>
      <p class="small">${esc(s.why_included)} Planting ${esc(s.planting)} (${s.parameters.stages_days.reduce((a, b) => a + b, 0)} days).</p>
      <p class="small">Root zone ${s.result.root_depth_m} m · TAW ${s.result.taw_mm ?? "—"} mm · RAW ${s.result.raw_mm ?? "—"} mm
        · sensitivity TAW (1/3–15 bar) ${s.result.taw_fc_wp_mm ?? "—"} mm · seasons ${s.result.seasons_simulated}
        ${Object.entries(s.result.seasons_excluded).map(([k, v]) => ` · excluded ${v.count} (${esc(v.reason)})`).join("")}</p>
      <p class="small"><strong>Rotation note</strong> (${esc(s.rotation.review_state)}): ${esc(s.rotation.text)}</p>
    </div>`).join("")}
    ${r.rejected.length ? `<h2>Not evaluated</h2><ul>${r.rejected.map((x) => `<li>${esc(x.crop)}: ${esc(x.reason)}</li>`).join("")}</ul>` : ""}
    <details><summary>What we know</summary><div><div class="table-wrap"><table><thead><tr><th>Input</th><th>Status</th><th>Source</th><th>Effect</th></tr></thead>
      <tbody>${r.inputs.map((i) => `<tr><td>${esc(i.name)}</td><td>${esc(i.state)}</td><td>${esc(i.source || "—")}</td><td>${esc(i.effect)}</td></tr>`).join("")}</tbody></table></div></div></details>
    <details><summary>Equations used</summary><div>${r.equations.map((id) => `<p><strong>${esc(id)}</strong> <span class="eq">${esc(equations[id]?.formula || "")}</span> [${esc(equations[id]?.unit || "")}]</p>`).join("")}
      <p class="small muted">${esc(equations["FAO56-Eq6"]?.reference || "")}</p></div></details>
    <details><summary>Seasons table (every simulated value)</summary><div>${r.strategies.map((s) => `<h3>${esc(s.name)}</h3><div class="table-wrap"><table>
      <thead><tr><th>Year</th><th class="num">ET0</th><th class="num">ETc</th><th class="num">Rain</th><th class="num">Deficit</th><th class="num">Stress d</th><th class="num">Net irr.</th></tr></thead>
      <tbody>${s.result.seasons.map((x) => `<tr><td>${x.year}</td><td class="num">${x.et0}</td><td class="num">${x.etc_standard}</td><td class="num">${x.precipitation}</td><td class="num">${x.rainfed_deficit ?? "—"}</td><td class="num">${x.rainfed_stress_days ?? "—"}</td><td class="num">${x.irrigated_net_irrigation ?? "—"}</td></tr>`).join("")}</tbody></table></div>`).join("")}</div></details>
    <details><summary>Limitations</summary><div><ul>${r.limitations.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div></details>
    <details><summary>Sources</summary><div>
      <p class="small">Weather: ${esc(w.provider)} ${esc(w.product)} ${esc(w.version)} (sources ${esc(w.sources.join(", "))}), ${esc(w.period[0])} to ${esc(w.period[1])}, retrieved ${esc(w.retrieved_utc)}, SHA-256 ${esc(w.content_sha256.slice(0, 16))}…</p>
      <p class="small">${esc(w.reference)}</p>
      ${r.provenance.soil ? `<p class="small">Soil: ${esc(r.provenance.soil.product)}, map unit ${esc(r.provenance.soil.returned_support.mukey)}, ${esc(r.provenance.soil.selection)}. ${esc(r.provenance.soil.reference)}</p>` : ""}
      <p class="small">Versions: engine ${esc(r.versions.engine)}, crop catalog ${esc(r.versions.crop_catalog)}, boundary ${esc(r.versions.boundary)}.</p></div></details>
    <div class="actions no-print">
      <button id="print">Print or save as PDF</button>
      ${r.analysis_id ? `<a class="button" href="${API}/analyses/${encodeURIComponent(r.analysis_id)}/report" target="_blank" rel="noopener">Markdown report</a>` : ""}
      <button id="back">Change inputs</button>
    </div>`;
  document.getElementById("print").onclick = () => window.print();
  document.getElementById("back").onclick = () => renderForm();
  panel.focus();
}

// ---------- start ----------
(async () => {
  initMap();
  try { catalog = await getJSON(`${API}/crops`); } catch { catalog = { crops: [] }; }
  if (form.lat !== "" && form.lon !== "") setPoint(Number(form.lat), Number(form.lon), form.mode); else renderForm();
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => { /* app works without it */ });
})();
