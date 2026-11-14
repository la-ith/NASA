// Field Shift web app: the section 8 screens. Plain JavaScript; every label and number comes from the API.
const API = "/api/v1";
const CANDIDATE_SEASON = "2026/27";
const LAST_SEASON_YEAR = 2025; // the season right before the candidate season
const MAX_SEASONS = 5;
const TIMEOUT_MS = 30000;
const NOTICE =
  "Field Shift compares options using the information and sources shown. Gridded climate data may not represent " +
  "conditions within your exact field, and historical conditions do not predict next season. Review choices with " +
  "local agricultural expertise.";
const STEPS = [
  ["home", "Start"], ["field", "Field"], ["history", "History"], ["goal", "Goal"],
  ["review", "Review"], ["analyze", "Analyze"], ["compare", "Compare"],
];
const GOALS = {
  conserve_water: ["Conserve water", "Water fit is shown first."],
  improve_soil_rotation: ["Improve soil and rotation", "Rotation/soil is shown first."],
  balance_both: ["Balance both", "Water fit, then rotation/soil."],
};
const CRITERION = { rotation_soil: "Rotation/soil", water_fit: "Water fit", risk: "Risk", hard_constraint: "Hard constraint" };
const LABEL = {
  favorable: "Favorable", mixed: "Mixed", concern: "Concern",
  insufficient_evidence: "Insufficient evidence", rejected: "Rejected",
};
const IRRIGATION = { "rain-fed": "Rain-fed", irrigated: "Irrigated", mixed: "Mixed", unknown: "Unknown" };

const view = document.getElementById("view");
document.getElementById("notice").textContent = NOTICE;

// Browser storage is a per-viewer convenience only; the app works without it.
const store = {
  get(key, fallback) {
    try { const v = localStorage.getItem(key); return v ? JSON.parse(v) : fallback; } catch { return fallback; }
  },
  set(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* storage unavailable */ } },
};

const seasonLabel = (y) => `${y}/${String((y + 1) % 100).padStart(2, "0")}`;
const round1 = (x) => Math.round(Number(x) * 10) / 10;
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const badge = (label) => `<span class="badge ${esc(label)}">${esc(LABEL[label] || label)}</span>`;

function newDraft() {
  return {
    mode: "live",
    field: { label: "", lat: "31.5", lon: "35.1", area: { value: "", unit: "dunum" }, irrigation: "", soil: "unknown" },
    history: [{ season: seasonLabel(LAST_SEASON_YEAR), crop: "" }],
    goal: "",
    current_practice_crop: "",
    extra_candidates: [],
  };
}
let draft = store.get("fs-draft", null) || newDraft();
let result = store.get("fs-result", null);
let crops = null;
let lastErrors = [];
const saveDraft = () => store.set("fs-draft", draft);

async function loadCrops() {
  if (!crops) {
    const response = await fetch(`${API}/crops`);
    if (!response.ok) throw new Error("Could not load the crop list.");
    crops = await response.json();
  }
  return crops;
}
const candidateNames = () => (crops ? crops.candidates.map((c) => c.name) : []);
const lastCrop = () => draft.history[draft.history.length - 1].crop;
const needsCurrentChoice = () => lastCrop() !== "" && !candidateNames().includes(lastCrop());

// ---------- validation (mirrors section 6.3; the API checks everything again) ----------
function fieldErrors() {
  const f = draft.field, errors = {};
  const lat = round1(f.lat), lon = round1(f.lon);
  if (f.lat === "" || f.lon === "" || Number.isNaN(lat) || Number.isNaN(lon)) errors.location = "Enter a latitude and longitude.";
  else if (lat !== 31.5 || lon !== 35.1) errors.location = "This version supports only the Hebron pilot area (31.5 N, 35.1 E).";
  if (!(Number(f.area.value) > 0)) errors.area = "Enter an area greater than zero.";
  if (!f.irrigation) errors.irrigation = "Choose an irrigation type.";
  return errors;
}
function historyErrors() {
  const errors = {};
  if (draft.history.some((s) => !s.crop)) errors.history = "Choose a crop or Unknown for every season.";
  if (needsCurrentChoice() && !candidateNames().includes(draft.current_practice_crop)) {
    errors.current = "Choose the crop for current practice.";
  }
  return errors;
}
const goalErrors = () => (draft.goal ? {} : { goal: "Choose one goal." });

function requestBody() {
  return {
    mode: draft.mode,
    field: {
      label: draft.field.label || null,
      lat: round1(draft.field.lat), lon: round1(draft.field.lon),
      area: { value: Number(draft.field.area.value), unit: draft.field.area.unit },
      irrigation: draft.field.irrigation, soil: draft.field.soil || "unknown",
    },
    history: draft.history,
    candidate_season: CANDIDATE_SEASON,
    goal: draft.goal,
    current_practice_crop: needsCurrentChoice() ? draft.current_practice_crop : null,
    extra_candidates: draft.mode === "sample" ? draft.extra_candidates : [],
  };
}

// ---------- routing ----------
function go(name) { location.hash = `#/${name}`; }
function setStepper(active) {
  const index = STEPS.findIndex(([key]) => key === active);
  document.getElementById("stepper").innerHTML = STEPS.map(([key, title], i) =>
    `<li${i === index ? ' aria-current="step"' : ""}${i < index ? ' class="done"' : ""}>${i + 1}. ${title}</li>`).join("");
}
function show(html, step) {
  setStepper(step);
  view.innerHTML = html;
  view.focus();
  window.scrollTo(0, 0);
}

async function route() {
  const [name = "home", arg] = location.hash.replace(/^#\/?/, "").split("/");
  try {
    if (["field", "history", "review"].includes(name)) await loadCrops();
    ({ home, field, history, goal, review, analyze, compare, evidence, result: sharedResult }[name] || home)(arg);
  } catch (err) {
    show(`<h1>Something went wrong</h1><div class="errors">${esc(err.message)}</div>
      <p class="actions"><a class="button" href="#/home">Back to start</a></p>`, "home");
  }
}
window.addEventListener("hashchange", route);

// ---------- screen 1: home ----------
function home() {
  show(`
    <h1>Compare next season's crop options for one field</h1>
    <p>Field Shift shows how a few crop choices differ, why they differ, and what the evidence cannot tell you,
    using NASA POWER rainfall history and transparent, cited rules.</p>
    <div class="actions">
      <button class="primary" id="start">Start a field comparison</button>
      <button id="sample">Try sample field</button>
    </div>
    <div class="panel">
      <h2>What it can and cannot do</h2>
      <ul>
        <li>It compares three plans: your current practice and two alternatives, for the 2026/27 winter season.</li>
        <li>It uses historical rainfall for the wider area. It is not a forecast and not a field measurement.</li>
        <li>It does not predict yield or profit, and it does not choose for you.</li>
        <li>This version covers one pilot area near Hebron, and its rules have not yet been reviewed by an agronomist.</li>
      </ul>
    </div>
    ${result ? `<p><a href="#/compare">Open your last comparison</a></p>` : ""}`, "home");
  document.getElementById("start").onclick = () => { draft.mode = "live"; draft.extra_candidates = []; saveDraft(); go("field"); };
  document.getElementById("sample").onclick = async () => {
    const response = await fetch(`${API}/demo`);
    const demo = (await response.json()).request;
    draft = {
      mode: "sample",
      field: { ...demo.field, label: demo.field.label, lat: String(demo.field.lat), lon: String(demo.field.lon),
               area: { value: String(demo.field.area.value), unit: demo.field.area.unit } },
      history: demo.history, goal: demo.goal, current_practice_crop: "", extra_candidates: demo.extra_candidates,
    };
    saveDraft();
    go("review");
  };
}

// ---------- screen 2: field ----------
function field() {
  const f = draft.field, e = lastErrors;
  show(`
    <h1>Your field</h1>
    <form id="form" novalidate>
      <label for="label">Field name <span class="hint">(optional)</span></label>
      <input id="label" type="text" value="${esc(f.label)}" autocomplete="off">
      <fieldset>
        <legend>Location</legend>
        <p class="hint">Typed coordinates work without a map. The app rounds them to 0.1° and never stores exact coordinates.</p>
        <div class="row">
          <div><label for="lat">Latitude (°N)</label><input id="lat" type="number" inputmode="decimal" step="0.01" value="${esc(f.lat)}"></div>
          <div><label for="lon">Longitude (°E)</label><input id="lon" type="number" inputmode="decimal" step="0.01" value="${esc(f.lon)}"></div>
        </div>
        <p class="small" id="rounded"></p>
        ${e.location ? `<p class="error">${esc(e.location)}</p>` : ""}
      </fieldset>
      <div class="row">
        <div><label for="area">Area</label><input id="area" type="number" inputmode="decimal" min="0" step="any" value="${esc(f.area.value)}"></div>
        <div><label for="unit">Unit</label><select id="unit">${["dunum", "hectare", "acre"].map((u) =>
          `<option${u === f.area.unit ? " selected" : ""}>${u}</option>`).join("")}</select></div>
      </div>
      ${e.area ? `<p class="error">${esc(e.area)}</p>` : ""}
      <fieldset>
        <legend>Irrigation</legend>
        ${Object.entries(IRRIGATION).map(([v, t]) => `<label class="choice"><input type="radio" name="irr" value="${v}"${f.irrigation === v ? " checked" : ""}> ${t}</label>`).join("")}
        ${e.irrigation ? `<p class="error">${esc(e.irrigation)}</p>` : ""}
      </fieldset>
      <label for="soil">Soil type <span class="hint">(optional; shown as context, not used by any rule)</span></label>
      <select id="soil">${["unknown", "clay", "clay loam", "loam", "sandy loam", "sandy", "rocky"].map((s) =>
        `<option value="${s}"${s === f.soil ? " selected" : ""}>${s === "unknown" ? "I don't know" : s}</option>`).join("")}</select>
      <div class="actions"><a class="button" href="#/home">Back</a><button class="primary" type="submit">Next: crop history</button></div>
    </form>`, "field");
  const read = () => {
    f.label = document.getElementById("label").value.trim();
    f.lat = document.getElementById("lat").value; f.lon = document.getElementById("lon").value;
    f.area.value = document.getElementById("area").value; f.area.unit = document.getElementById("unit").value;
    f.irrigation = (document.querySelector('input[name="irr"]:checked') || {}).value || "";
    f.soil = document.getElementById("soil").value;
    document.getElementById("rounded").textContent = f.lat !== "" && f.lon !== ""
      ? `The app will use ${round1(f.lat).toFixed(1)} N, ${round1(f.lon).toFixed(1)} E.` : "";
    saveDraft();
  };
  read();
  document.getElementById("form").oninput = read;
  document.getElementById("form").onsubmit = (ev) => {
    ev.preventDefault(); read();
    lastErrors = fieldErrors();
    if (Object.keys(lastErrors).length) field(); else { lastErrors = []; go("history"); }
  };
}

// ---------- screen 3: crop history ----------
function history() {
  const e = lastErrors;
  const options = (selected) => `<option value=""${selected ? "" : " selected"}>Choose…</option>` +
    crops.history_choices.map((c) => `<option value="${esc(c.name)}"${c.name === selected ? " selected" : ""}>${
      c.name === "unknown" ? "Unknown" : `${esc(c.name)} (${esc(c.type)})`}</option>`).join("");
  show(`
    <h1>Crop history</h1>
    <p>Enter what grew in each recent season (1 October to 31 May). Choose Unknown when you are not sure.
    Missing history can limit the comparison; the app never fills gaps for you.</p>
    <form id="form" novalidate>
      ${draft.history.map((s, i) => `
        <label for="crop-${i}">Season ${esc(s.season)}${i === draft.history.length - 1 ? " (last season)" : ""}</label>
        <select id="crop-${i}" data-i="${i}">${options(s.crop)}</select>`).join("")}
      <div class="actions">
        <button type="button" id="add"${draft.history.length >= MAX_SEASONS ? " disabled" : ""}>Add an earlier season</button>
        <button type="button" id="remove"${draft.history.length <= 1 ? " disabled" : ""}>Remove the earliest season</button>
      </div>
      ${e.history ? `<p class="error">${esc(e.history)}</p>` : ""}
      <div id="current"></div>
      <div class="actions"><a class="button" href="#/field">Back</a><button class="primary" type="submit">Next: goal</button></div>
    </form>`, "history");
  const renderCurrent = () => {
    const box = document.getElementById("current");
    if (!needsCurrentChoice()) { box.innerHTML = ""; return; }
    const why = lastCrop() === "unknown" ? "is unknown" : `(${lastCrop()}) is not a crop this version can plan for`;
    box.innerHTML = `<fieldset><legend>Current practice</legend>
      <p class="hint">The last season's crop ${esc(why)}, so it cannot be repeated automatically. Which crop would you grow if nothing changed?</p>
      ${candidateNames().map((c) => `<label class="choice"><input type="radio" name="current" value="${c}"${draft.current_practice_crop === c ? " checked" : ""}> ${c}</label>`).join("")}
      ${e.current ? `<p class="error">${esc(e.current)}</p>` : ""}</fieldset>`;
    box.querySelectorAll('input[name="current"]').forEach((r) => { r.onchange = () => { draft.current_practice_crop = r.value; saveDraft(); }; });
  };
  renderCurrent();
  document.querySelectorAll("select[data-i]").forEach((sel) => {
    sel.onchange = () => { draft.history[Number(sel.dataset.i)].crop = sel.value; saveDraft(); renderCurrent(); };
  });
  document.getElementById("add").onclick = () => {
    const first = Number(draft.history[0].season.slice(0, 4));
    draft.history.unshift({ season: seasonLabel(first - 1), crop: "" }); saveDraft(); history();
  };
  document.getElementById("remove").onclick = () => { draft.history.shift(); saveDraft(); history(); };
  document.getElementById("form").onsubmit = (ev) => {
    ev.preventDefault();
    lastErrors = historyErrors();
    if (Object.keys(lastErrors).length) history(); else { lastErrors = []; go("goal"); }
  };
}

// ---------- screen 4: goal ----------
function goal() {
  const e = lastErrors;
  show(`
    <h1>Your goal</h1>
    <p>The goal changes the order of the criteria and which trade-off the summary names. It never changes a label.</p>
    <form id="form" novalidate><fieldset><legend>Choose one goal</legend>
      ${Object.entries(GOALS).map(([v, [t, h]]) => `<label class="choice"><input type="radio" name="goal" value="${v}"${draft.goal === v ? " checked" : ""}>
        <span>${t}<br><span class="hint">${h}</span></span></label>`).join("")}
      ${e.goal ? `<p class="error">${esc(e.goal)}</p>` : ""}</fieldset>
      <div class="actions"><a class="button" href="#/history">Back</a><button class="primary" type="submit">Next: review</button></div>
    </form>`, "goal");
  document.querySelectorAll('input[name="goal"]').forEach((r) => { r.onchange = () => { draft.goal = r.value; saveDraft(); }; });
  document.getElementById("form").onsubmit = (ev) => {
    ev.preventDefault();
    lastErrors = goalErrors();
    if (Object.keys(lastErrors).length) goal(); else { lastErrors = []; go("review"); }
  };
}

// ---------- screen 5: review ----------
function review() {
  const f = draft.field;
  const problems = { ...fieldErrors(), ...historyErrors(), ...goalErrors() };
  const plansText = (() => {
    const current = needsCurrentChoice() ? draft.current_practice_crop : lastCrop();
    if (!current) return "Chosen once the history is complete.";
    const others = candidateNames().filter((c) => c !== current);
    return `A: ${current} (current practice); B: ${others[0]}; C: ${others[1]}` +
      (draft.mode === "sample" && draft.extra_candidates.length ? `; D: ${draft.extra_candidates[0]} (sample test of the rejection path)` : "");
  })();
  show(`
    <h1>Review your inputs</h1>
    ${draft.mode === "sample" ? `<div class="banner">Sample field: illustrative data, not a real farm.</div>` : ""}
    <div class="panel"><dl class="facts">
      <dt>Field</dt><dd>${esc(f.label || "Unnamed field")} <a href="#/field">Edit</a></dd>
      <dt>Location used</dt><dd>${round1(f.lat).toFixed(1)} N, ${round1(f.lon).toFixed(1)} E (rounded)</dd>
      <dt>Area</dt><dd>${esc(f.area.value)} ${esc(f.area.unit)}</dd>
      <dt>Irrigation</dt><dd>${esc(IRRIGATION[f.irrigation] || "Not chosen")}</dd>
      <dt>Soil type</dt><dd>${esc(f.soil === "unknown" ? "I don't know" : f.soil)}</dd>
      <dt>History</dt><dd>${draft.history.map((s) => `${esc(s.season)}: ${esc(s.crop || "not chosen")}`).join("; ")} <a href="#/history">Edit</a></dd>
      <dt>Goal</dt><dd>${esc(GOALS[draft.goal]?.[0] || "Not chosen")} <a href="#/goal">Edit</a></dd>
      <dt>Plans for ${CANDIDATE_SEASON}</dt><dd>${esc(plansText)}</dd>
    </dl></div>
    <fieldset><legend>Climate data</legend>
      <label class="choice"><input type="radio" name="mode" value="live"${draft.mode === "live" ? " checked" : ""}> Live NASA POWER data</label>
      <label class="choice"><input type="radio" name="mode" value="sample"${draft.mode === "sample" ? " checked" : ""}> Saved sample record (clearly labelled)</label>
    </fieldset>
    ${Object.keys(problems).length ? `<div class="errors"><p>Please fix these first:</p><ul>${Object.values(problems).map((p) => `<li>${esc(p)}</li>`).join("")}</ul></div>` : ""}
    <div class="actions"><a class="button" href="#/goal">Back</a>
      <button class="primary" id="run"${Object.keys(problems).length ? " disabled" : ""}>Run analysis</button></div>`, "review");
  document.querySelectorAll('input[name="mode"]').forEach((r) => { r.onchange = () => { draft.mode = r.value; saveDraft(); review(); }; });
  document.getElementById("run").onclick = () => go("analyze");
}

// ---------- screen 6: analysis progress and every error state ----------
async function analyze() {
  if (!navigator.onLine) {
    show(`<h1>You are offline</h1><p>The analysis needs a connection. Your inputs are kept.</p>
      ${result ? `<p><a href="#/compare">Open your last saved comparison</a> (from ${esc(new Date(result._savedAt).toLocaleString())})</p>` : ""}
      <div class="actions"><a class="button" href="#/review">Back to review</a><button class="primary" id="retry">Try again</button></div>`, "analyze");
    document.getElementById("retry").onclick = analyze;
    return;
  }
  const source = draft.mode === "sample" ? "the saved sample record" : "NASA POWER (daily rainfall, PRECTOTCORR, 1991–2026)";
  show(`<h1>Preparing your comparison</h1>
    <p>Source: ${esc(source)}.</p>
    <ol class="stages" aria-live="polite">
      <li>Checking inputs</li><li>Retrieving climate data</li><li>Checking the data against the request</li>
      <li>Checking the data against the local station</li><li>Preparing the comparison</li>
    </ol>
    <p class="muted" id="elapsed" aria-live="off">Working…</p>`, "analyze");
  const started = Date.now();
  const timer = setInterval(() => {
    const el = document.getElementById("elapsed");
    if (el) el.textContent = `Working… ${Math.round((Date.now() - started) / 1000)} s`;
  }, 1000);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const response = await fetch(`${API}/analyses`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestBody()), signal: controller.signal,
    });
    const body = await response.json();
    if (response.ok) {
      result = { ...body, _savedAt: Date.now() };
      store.set("fs-result", result);
      go("compare");
      return;
    }
    failure(body.error || { code: "unknown", message: `HTTP ${response.status}` });
  } catch (err) {
    failure(err.name === "AbortError" ? { code: "timeout" } : navigator.onLine ? { code: "network", message: err.message } : { code: "offline" });
  } finally {
    clearInterval(timer); clearTimeout(timeout);
  }
}

function failure(error) {
  const messages = {
    invalid_input: ["Some inputs need fixing", "The server checked your inputs and found a problem."],
    provider_error: ["NASA POWER did not respond", "Live rainfall data could not be retrieved. Your inputs are kept."],
    data_integrity: ["Data error", "NASA's response did not match the request exactly, so it was not used."],
    no_data: ["No usable data", "The climate record had no valid days for this request."],
    timeout: ["This is taking too long", "The analysis did not finish within 30 seconds. Your inputs are kept."],
    offline: ["You are offline", "The analysis needs a connection. Your inputs are kept."],
  };
  const [title, text] = messages[error.code] || ["Something went wrong", "The analysis could not be completed."];
  const details = error.code === "invalid_input"
    ? `<ul>${(error.fields || []).map((f) => `<li>${esc(String(f.msg).replace(/^Value error, /, ""))}</li>`).join("")}</ul>`
    : error.message ? `<p class="small">${esc(error.message)}</p>` : "";
  const sample = error.code !== "invalid_input" && draft.mode !== "sample";
  show(`<h1>${esc(title)}</h1><div class="errors"><p>${esc(text)}</p>${details}</div>
    <div class="actions"><a class="button" href="#/review">Back to review</a>
      ${error.code !== "invalid_input" ? `<button class="primary" id="retry">Retry</button>` : ""}
      ${sample ? `<button id="use-sample">Use sample data</button>` : ""}</div>`, "analyze");
  document.getElementById("retry")?.addEventListener("click", analyze);
  document.getElementById("use-sample")?.addEventListener("click", () => { draft.mode = "sample"; saveDraft(); analyze(); });
}

// ---------- screen 7: comparison (also the printable report) ----------
function planCard(p, order) {
  if (p.status === "rejected") {
    return `<article class="plan"><span class="role">Plan ${esc(p.id)} · not evaluated</span><h3>${esc(p.crop)}</h3>
      <p>${badge("rejected")} ${esc(p.rejection_reason)}</p><p class="small muted">${esc(p.why_included)}</p></article>`;
  }
  const byName = Object.fromEntries(p.criteria.map((c) => [c.criterion, c]));
  const benefit = order.map((k) => byName[k]).find((c) => c.label === "favorable");
  const concern = order.map((k) => byName[k]).find((c) => c.label === "concern");
  return `<article class="plan${p.type === "current_practice" ? " current" : ""}">
    <span class="role">Plan ${esc(p.id)} · ${p.type === "current_practice" ? "current practice" : "alternative"}</span>
    <h3>${esc(p.display)}</h3>
    <p class="small muted">${esc(p.why_included)}</p>
    <ul class="criteria">${order.map((k) => `<li><span>${CRITERION[k]}</span>${badge(byName[k].label)}</li>`).join("")}</ul>
    <p class="small"><strong>Key benefit:</strong> ${benefit ? `${CRITERION[benefit.criterion]}: ${esc(benefit.reason)}` : "None identified."}</p>
    <p class="small"><strong>Concern:</strong> ${concern ? `${CRITERION[concern.criterion]}: ${esc(concern.reason)}` : "None identified."}</p>
    <a class="button push no-print" href="#/evidence/${esc(p.id)}">Why? Evidence and what we know</a>
  </article>`;
}

function compare() {
  if (!result) { show(`<h1>No comparison yet</h1><p><a href="#/home">Start a comparison</a></p>`, "compare"); return; }
  const r = result, d = r.data, order = r.criterion_order;
  const current = r.plans.filter((p) => p.type === "current_practice");
  const others = r.plans.filter((p) => p.type !== "current_practice" && p.status === "evaluated");
  const rejected = r.plans.filter((p) => p.status === "rejected");
  show(`
    <h1>Comparison for ${esc(r.candidate_season)}</h1>
    ${r.banners.sample_data ? `<div class="banner">Sample data: illustrative, not a live NASA call.</div>` : ""}
    ${r.banners.illustrative_rules ? `<div class="banner">Illustrative rules, not reviewed by an agricultural specialist.</div>` : ""}
    <div class="panel"><p><strong>${esc(r.summary)}</strong></p>
      <p class="small muted">Goal: ${esc(GOALS[r.goal][0])}. The goal orders the criteria; it never changes a label.</p></div>
    <div class="panel"><dl class="facts">
      <dt>Field</dt><dd>${esc(r.field.label || "Unnamed field")}, ${r.field.lat.toFixed(1)} N, ${r.field.lon.toFixed(1)} E, ${esc(IRRIGATION[r.field.irrigation])}</dd>
      <dt>History</dt><dd>${r.history.map((s) => `${esc(s.season)}: ${esc(s.crop)}`).join("; ")}</dd>
      <dt>Rainfall data</dt><dd>NASA POWER ${esc(d.parameter)} (${esc(d.api_version)}), ${esc(d.period[0])} to ${esc(d.period[1])}, ${d.valid_days} valid days, ${d.missing_days} missing</dd>
      <dt>Site check</dt><dd>${esc(d.site_check.result.replace("_", " "))}: ${esc(d.site_check.reason)}</dd>
    </dl></div>
    <h2>Plans</h2>
    <div class="plans">${[...current, ...others].map((p) => planCard(p, order)).join("")}</div>
    ${rejected.length ? `<h2>Not evaluated</h2><div class="plans">${rejected.map((p) => planCard(p, order)).join("")}</div>` : ""}
    <div class="actions no-print">
      <a class="button" href="#/evidence">Evidence for all plans</a>
      <button id="print">Print or save as PDF</button>
      <button id="share">Copy share link</button>
      <a class="button" href="#/review">Change inputs</a>
    </div>
    <p id="share-status" class="small muted no-print" aria-live="polite"></p>
    <div class="panel"><h2>Limits of this comparison</h2><ul>${r.limitations.map((l) => `<li>${esc(l)}</li>`).join("")}</ul>
      <h3>Questions to ask locally</h3><ul>${r.local_questions.map((q) => `<li>${esc(q)}</li>`).join("")}</ul>
      <p class="small">Report date: ${esc(new Date(r._savedAt || Date.now()).toISOString().slice(0, 10))}. Analysis ${esc(r.analysis_id)}, rules ${esc(r.versions.rules)}, engine ${esc(r.versions.engine)}.</p>
      <p class="small">${esc(r.acknowledgement)} ${esc(r.data_reference)}</p></div>`, "compare");
  document.getElementById("print").onclick = () => window.print();
  document.getElementById("share").onclick = async () => {
    const link = `${location.origin}${location.pathname}#/result/${r.analysis_id}`; // no coordinates in the link
    try { await navigator.clipboard.writeText(link); document.getElementById("share-status").textContent = "Link copied."; }
    catch { document.getElementById("share-status").textContent = link; }
  };
}

// ---------- screen 8: evidence ----------
function rainfallChart(d) {
  const seasons = d.seasons, station = d.site_check.station_mm, mean = d.indicators.baseline_mean_mm;
  const recent = new Set(Object.keys(d.indicators.anomalies_pct));
  const max = Math.max(...seasons.map((s) => s.total_mm || 0), station || 0) * 1.1;
  const W = 700, H = 240, left = 44, bottom = 28, top = 10, plotH = H - bottom - top, step = (W - left - 8) / seasons.length;
  const y = (v) => top + plotH - (v / max) * plotH;
  const bars = seasons.map((s, i) => s.total_mm == null
    ? `<text x="${left + i * step + step / 2}" y="${y(0) - 4}" font-size="9" text-anchor="middle" fill="currentColor">n/a</text>`
    : `<rect x="${left + i * step + 1}" y="${y(s.total_mm)}" width="${step - 2}" height="${y(0) - y(s.total_mm)}"
        fill="var(${recent.has(s.season) ? "--chart-recent" : "--chart-bar"})"><title>${esc(s.season)}: ${s.total_mm} mm</title></rect>`).join("");
  const tickStep = max > 800 ? 200 : 100;
  const ticks = Array.from({ length: Math.floor(max / tickStep) + 1 }, (_, i) => i * tickStep)
    .map((v) => `<text x="${left - 6}" y="${y(v) + 4}" font-size="10" text-anchor="end" fill="currentColor">${v}</text>
      <line x1="${left}" x2="${W - 8}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)"/>`).join("");
  const labels = seasons.map((s, i) => i % 5 === 0
    ? `<text x="${left + i * step + step / 2}" y="${H - 10}" font-size="10" text-anchor="middle" fill="currentColor">${esc(s.season)}</text>` : "").join("");
  const meanLine = mean == null ? "" : `<line x1="${left}" x2="${W - 8}" y1="${y(mean)}" y2="${y(mean)}" stroke="var(--chart-line)" stroke-width="2"/>`;
  const stationLine = station == null ? "" : `<line x1="${left}" x2="${W - 8}" y1="${y(station)}" y2="${y(station)}" stroke="var(--chart-station)" stroke-width="2" stroke-dasharray="6 4"/>`;
  return `<figure class="chart"><svg viewBox="0 0 ${W} ${H}" role="img" aria-labelledby="chart-title">
      <title id="chart-title">Seasonal rainfall (October to May) for the NASA POWER grid cell, ${esc(seasons[0].season)} to ${esc(seasons[seasons.length - 1].season)}. The table below lists every value.</title>
      ${ticks}${bars}${meanLine}${stationLine}${labels}</svg>
    <figcaption class="legend">
      <span><span class="swatch" style="background:var(--chart-bar)"></span>Season total, mm</span>
      <span><span class="swatch" style="background:var(--chart-recent)"></span>Recent 5 seasons</span>
      ${mean == null ? "" : `<span><span class="swatch" style="background:var(--chart-line)"></span>Baseline mean ${mean} mm</span>`}
      ${station == null ? "" : `<span><span class="swatch" style="background:var(--chart-station)"></span>Hebron station ${station} mm (dashed)</span>`}
    </figcaption></figure>`;
}

async function evidence(planId) {
  if (!result) { compare(); return; }
  const r = result, d = r.data, ind = d.indicators;
  let rules = [];
  try { rules = await (await fetch(`${API}/rules`)).json(); } catch { /* rules list is optional context */ }
  const plans = r.plans.filter((p) => !planId || p.id === planId);
  show(`
    <h1>Evidence${planId ? ` for plan ${esc(planId)}` : ""}</h1>
    <p><a href="#/compare">Back to the comparison</a></p>
    ${plans.map((p) => `<details open><summary>Plan ${esc(p.id)}: ${esc(p.display)}</summary><div>
      <p class="small muted">${esc(p.why_included)}</p>
      ${p.criteria.map((c) => `<h3>${CRITERION[c.criterion]} ${badge(c.label)}</h3>
        <p>${esc(c.explanation)}</p>
        <p class="small muted">Rule ${esc(c.rule || "none (history insufficient)")} · ${esc(c.rule_state)}</p>`).join("")}
      ${p.inputs.length ? `<h3>What we know</h3><div class="table-wrap"><table>
        <thead><tr><th>Input</th><th>Status</th><th>Source or default</th><th>Effect on this plan</th></tr></thead>
        <tbody>${p.inputs.map((i) => `<tr><td>${esc(i.name)}</td><td>${esc(i.state)}</td><td>${esc(i.source)}</td><td>${esc(i.effect)}</td></tr>`).join("")}</tbody>
      </table></div>` : ""}
    </div></details>`).join("")}
    <details open><summary>Rainfall evidence (NASA POWER)</summary><div>
      ${rainfallChart(d)}
      <dl class="facts">
        <dt>Baseline mean (I2)</dt><dd>${ind.baseline_mean_mm ?? "unavailable"} mm, seasons 1991/92–2020/21 (historical)</dd>
        <dt>Variability (I4)</dt><dd>${ind.baseline_cv_pct ?? "unavailable"}% coefficient of variation</dd>
        <dt>Recent shift (I6)</dt><dd>${ind.recent_shift_pct ?? "unavailable"}% versus the baseline; five seasons are too few to establish a trend</dd>
        <dt>Recent seasons (I3)</dt><dd>${Object.entries(ind.anomalies_pct).map(([s, v]) => `${esc(s)}: ${v > 0 ? "+" : ""}${v}%`).join("; ")}</dd>
        <dt>Site check</dt><dd>${esc(d.site_check.reason)} (grid cell ${d.site_check.cell_mm} mm, station ${d.site_check.station_mm} mm, ratio ${d.site_check.ratio})</dd>
        <dt>Grid cell</dt><dd>About 56 km × 59 km; average elevation ${d.cell_elevation_m} m</dd>
        <dt>Source</dt><dd>${esc(d.provider)} ${esc(d.parameter)}, ${esc(d.units)}, ${esc(d.api_version)}, sources ${esc(d.sources.join(", "))}, retrieved ${esc(d.retrieved_utc)}</dd>
        <dt>Coverage</dt><dd>${d.valid_days} valid days, ${d.missing_days} missing, ${d.quality_flags.length} flagged</dd>
      </dl>
      <h3>Season totals</h3><div class="table-wrap"><table>
        <thead><tr><th>Season</th><th class="num">Total (mm)</th><th class="num">Valid days</th></tr></thead>
        <tbody>${d.seasons.map((s) => `<tr><td>${esc(s.season)}</td><td class="num">${s.total_mm ?? "unavailable"}</td><td class="num">${s.valid_days} of ${s.days}</td></tr>`).join("")}</tbody>
      </table></div>
    </div></details>
    <details><summary>Rules used (rule set ${esc(r.versions.rules)})</summary><div>
      <p class="small">The 80/50 and 20/35 cut-offs are team choices made so labels are reproducible; they are not agronomic standards.</p>
      <div class="table-wrap"><table><thead><tr><th>Rule</th><th>Condition</th><th>Effect</th><th>Status</th></tr></thead>
        <tbody>${rules.map((x) => `<tr><td>${esc(x.code)}</td><td>${esc(x.condition)}</td><td>${esc(x.effect)}</td><td>${esc(x.review_state)}</td></tr>`).join("")}</tbody></table></div>
    </div></details>
    <details><summary>Limits and questions to ask locally</summary><div>
      <ul>${r.limitations.map((l) => `<li>${esc(l)}</li>`).join("")}</ul>
      <ul>${r.local_questions.map((q) => `<li>${esc(q)}</li>`).join("")}</ul>
      <p class="small">${esc(r.acknowledgement)} ${esc(r.data_reference)}</p>
    </div></details>`, "compare");
}

// ---------- shared link: GET a saved analysis by ID ----------
async function sharedResult(id) {
  show(`<h1>Loading saved comparison…</h1>`, "compare");
  const response = await fetch(`${API}/analyses/${encodeURIComponent(id || "")}`);
  if (!response.ok) { show(`<h1>Comparison not found</h1><p><a href="#/home">Start a comparison</a></p>`, "compare"); return; }
  result = { ...(await response.json()), _savedAt: Date.now() };
  store.set("fs-result", result);
  go("compare");
}

if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => { /* app works without it */ });
route();
