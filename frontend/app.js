// Farmer-first Field Shift interface. Scientific calculations stay on the API.
import {installLayers} from '/map-layers.js?v=6';
import {soilLayersSection, wireSoilLayers} from '/soil-profile.js?v=2';
const API = "/api/v2";
const VIEWS = {
  lower48: [[-125, 24], [-66.5, 49.5]],
  alaska: [[-180, 51], [-129, 71.5]],
  hawaii: [[-160.6, 18.8], [-154.7, 22.3]],
};
const GOALS = {
  conserve_water: "Save irrigation water",
  reduce_drought_stress: "Lower drought stress",
  improve_soil_rotation: "Improve the crop rotation",
};
const PRIORITIES = { improve_soil: "Improve soil health", livestock_feed: "Grow livestock feed", economics: "Keep costs and income workable", reduce_risk: "Lower weather risk" };
const SOIL_TEXTURES = [["unknown", "I don’t know"], ["sand", "Mostly sandy"], ["loam", "Loamy / balanced"], ["clay", "Mostly clay"], ["silt", "Mostly silty"], ["mixed", "Different across the field"]];
const SOIL_TESTS = [["unknown", "I don’t know"], ["recent", "Yes, in the last 3 years"], ["old", "Yes, but more than 3 years ago"], ["none", "No soil test"]];
const DRAINAGE = [["unknown", "I don’t know"], ["fast", "Drains quickly"], ["moderate", "At an average pace"], ["slow", "Slowly / water can stand"]];
const SLOPES = [["unknown", "I don’t know"], ["flat", "Mostly flat"], ["gentle", "Gentle slope"], ["steep", "Steep or uneven"]];
const WATER_SOURCES = [["unknown", "Not sure / no irrigation"], ["rainfall", "Rainfall only"], ["well", "Well or groundwater"], ["surface_water", "River, pond or canal"], ["municipal", "Public water supply"], ["mixed", "More than one source"]];
const LEVELS = [["unknown", "Not decided yet"], ["limited", "Limited"], ["moderate", "Some"], ["adequate", "Enough"]];
const ICON_PATHS = {
  plus: "M12 5v14M5 12h14", back: "M19 12H5m5 5-5-5 5-5", arrow: "M5 12h14m-5-5 5 5-5 5",
  pin: "M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11zM14.5 10a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0",
  sprout: "M12 20v-7m0 0c0-4 3-7 7-7 0 4-3 7-7 7Zm0-2C12 7 9.5 4 5 4c0 4.5 3 8 7 8M5 20h14",
  layers: "m12 3 9 5-9 5-9-5zm-9 9 9 5 9-5M3 16l9 5 9-5",
  drop: "M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z",
  soil: "M3 9h18M3 14h18M3 19h18M7 9V6M12 9V4M17 9V6",
  roots: "M12 3v8m0 0-4 5m4-5 4 5m-4-5v9M8 16l-2 4m10-4 2 4",
  alert: "M12 4 2.5 20h19zM12 10v4M12 17v.01",
  info: "M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0M12 11v5M12 8v.01",
  shield: "M12 3 5 6v6c0 4.5 3 7.5 7 9 4-1.5 7-4.5 7-9V6z",
  note: "M6 3h9l4 4v14H6zM14 3v5h5M9 12h7M9 16h5",
  chat: "M4 5h16v11H9l-5 4z",
  refresh: "M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7",
  check: "m5 12 5 5 9-10",
  sun: "M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4",
  source: "M4 5c0-1.1 3.6-2 8-2s8 .9 8 2-3.6 2-8 2-8-.9-8-2zm0 0v14c0 1.1 3.6 2 8 2s8-.9 8-2V5M4 12c0 1.1 3.6 2 8 2s8-.9 8-2",
  search: "M17 11a6 6 0 1 1-12 0 6 6 0 0 1 12 0M15.5 15.5 20 20",
};
const icon = (name, cls = "icon") => `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true"><path d="${ICON_PATHS[name]}"/></svg>`;
const selectOptions = (list, selected) => list.map(([value, label]) => `<option value="${value}"${selected === value ? " selected" : ""}>${label}</option>`).join("");
const errorBanner = (title, text) => `<div class="error-banner" role="alert">${icon("alert")}<div><strong>${esc(title)}</strong>${esc(text)}</div></div>`;
function stateCard(name, title, text, actions = "", kind = "") {
  return `<section class="state-card ${kind}"><span class="state-icon">${icon(name)}</span><h1>${esc(title)}</h1><p>${esc(text)}</p>${actions ? `<div class="button-row">${actions}</div>` : ""}</section>`;
}
const skeleton = () => `<section class="skeleton" aria-busy="true" aria-label="Loading"><i class="title"></i><i class="line"></i><i class="short"></i><i class="block"></i><i class="block"></i></section>`;
const panel = document.getElementById("panel");
const mapPane = document.getElementById("map-pane");
const mapStatus = document.getElementById("map-status");
const accountNav = document.getElementById("account-nav");
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
}[c]));

async function getJSON(url, options = {}) {
  const response = await fetch(url, { credentials: "same-origin", ...options });
  const body = response.status === 204 ? {} : await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = body?.error?.message || body?.detail || body?.error?.fields || `Request failed (${response.status})`;
    const message = Array.isArray(detail) ? detail.map((item) => item.msg).join("; ") : String(detail);
    throw Object.assign(new Error(message), { status: response.status, body });
  }
  return body;
}

let user = null;
let catalog = { crops: [] };
let fields = [];
let activeField = null;
let currentAnalysis = null;
let map = null;
let mapLayersReady = Promise.resolve(null);
let marker = null;
let fieldLocationToken = 0;
let chatSession = null;
let busy = false;
let authVersion = 0;

function setHeader() {
  accountNav.innerHTML = user
    ? `<button type="button" class="quiet-button" id="my-expert-requests">${icon("chat")}<span class="label-wide">Expert replies</span></button><button type="button" class="quiet-button account-chip" id="account-settings" aria-label="Account settings for ${esc(user.name)}"><span class="avatar" aria-hidden="true">${esc((user.name || "?").trim().charAt(0).toUpperCase())}</span><span class="label-wide">${esc(user.name)}</span></button><button type="button" class="quiet-button" id="sign-out">Sign out</button>`
    : `<button type="button" class="quiet-button" id="header-signin">Sign in</button>`;
  document.getElementById("sign-out")?.addEventListener("click", signOut);
  document.getElementById('my-expert-requests')?.addEventListener('click',myExpertRequests);
  document.getElementById('account-settings')?.addEventListener('click',accountSettings);
  document.getElementById('header-signin')?.addEventListener('click',()=>renderAuth());
}

// Tabs mirror the mockups: Home · My land · Plans · Field notes. Each screen marks its own tab.
function setTab(name, sample = false) {
  document.body.classList.remove("wide-results"); // only the plan comparison uses the full-width layout
  document.querySelectorAll("[data-tab]").forEach((button) => {
    if (button.dataset.tab === name) button.setAttribute("aria-current", "page"); else button.removeAttribute("aria-current");
  });
  const banner = document.getElementById("data-banner"), text = document.getElementById("data-banner-text");
  banner?.classList.toggle("sample", sample);
  if (text) text.textContent = sample
    ? "Saved example · real NASA and USDA records for Hays, Kansas, replayed through the model. Not your field."
    : "Research preview · historical NASA and USDA records replayed through FAO-56 equations. Not a forecast.";
  panel.focus?.({ preventScroll: true });
  window.scrollTo?.({ top: 0 });
}

function goTab(name) {
  if (busy) return; // an analysis or save is running; its own screen will finish first
  if (name === "home") return user ? showHome() : renderAuth();
  if (name === "land") return user ? showLands() : renderFieldEditor(activeField && !activeField.id ? activeField : null);
  if (name === "plans") return renderPlans();
  if (name === "notes") return renderNotesHub();
}
document.querySelectorAll("[data-tab]").forEach((button) => button.addEventListener("click", () => goTab(button.dataset.tab)));

function setMapVisible(visible) {
  mapPane.hidden = !visible;
  document.body.classList.toggle("map-active", visible);
  if (visible) {
    initMap();
    requestAnimationFrame(() => map?.resize());
  }
}

function initMap() {
  if (map || !window.maplibregl) return;
  map = new maplibregl.Map({
    container: "map", style: "https://tiles.openfreemap.org/styles/positron",
    bounds: VIEWS.lower48, fitBoundsOptions: { padding: 20 }, attributionControl: { compact: true },
  });
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
  // Start the attribution collapsed (still one tap away on the ⓘ button) so it doesn't cover the map.
  const collapseAttribution = () => document.querySelector("#map .maplibregl-ctrl-attrib")?.classList.remove("maplibregl-compact-show");
  map.once("styledata", collapseAttribution); map.once("load", collapseAttribution);
  let fallback = false;
  const blankStyle = { version: 8, sources: {}, layers: [{ id: "background", type: "background", paint: { "background-color": "#eef1ea" } }] };
  map.on("error", () => {
    if (!fallback && !map.isStyleLoaded()) {
      fallback = true;
      map.setStyle(blankStyle);
      mapStatus.textContent = "The map background is unavailable. You can still enter coordinates below.";
    }
  });
  map.on("style.load", () => {
    if (map.getSource("states")) return;
    map.addSource("states", { type: "geojson", data: `${API}/boundaries`, attribution: "U.S. Census Bureau 2023 cartographic boundaries" });
    map.addLayer({ id: "states-fill", type: "fill", source: "states", paint: { "fill-color": "#2f6b3b", "fill-opacity": 0.05 } });
    map.addLayer({ id: "states-line", type: "line", source: "states", paint: { "line-color": "#63876a", "line-width": 0.8 } });
  });
  map.on("click", (event) => {
    const { lat, lng } = event.lngLat.wrap();
    chooseLocation(Number(lat.toFixed(4)), Number(lng.toFixed(4)));
  });
  mapLayersReady = installLayers(map);
  document.querySelectorAll("[data-view]").forEach((button) => {
    button.onclick = () => map.fitBounds(VIEWS[button.dataset.view], { padding: 24 });
  });
}

function putMarker(lat, lon) {
  if (!map || !window.maplibregl) return;
  if (!marker) marker = new maplibregl.Marker({ color: "#b4532a" });
  marker.setLngLat([lon, lat]).addTo(map);
}

function renderAuth(mode = "login", error = "") {
  setMapVisible(false);
  busy = false;
  setHeader();
  setTab("home");
  const registering = mode === "register";
  panel.innerHTML = `
    <section class="home-hero">
      <div><p class="eyebrow">Plan with the evidence in view</p><h1>Plan your seasons around your field’s conditions</h1>
      <p class="lead">Start with what you know about your field. We bring in 25 past seasons of NASA weather and USDA soil records and replay them through published FAO-56 water equations for each crop.</p></div>
      <div class="button-row"><button type="button" class="primary" id="guest-explore">${icon("plus")} Add your field</button><button type="button" class="secondary-button" id="guest-demo">See a saved example</button></div>
    </section>
    <div class="two-col">
      <section class="auth-wrap" aria-labelledby="auth-title">
        <p class="eyebrow">${registering ? "New account" : "Welcome back"}</p>
        <h2 id="auth-title">${registering ? "Create your account" : "Sign in to keep your fields"}</h2>
        <p class="hint">Save fields, plans and private field notes across devices.</p>
        ${error ? errorBanner(registering ? "We couldn’t create your account" : "We couldn’t sign you in", error) : ""}
        <form id="auth-form" class="auth-form">
          ${registering ? `<label for="auth-name">Your name</label><input id="auth-name" name="name" type="text" autocomplete="name" required maxlength="80" placeholder="Name">` : ""}
          <label for="auth-email">Email address</label>
          <input id="auth-email" name="email" type="email" autocomplete="email" required maxlength="254" placeholder="you@example.com">
          <label for="auth-password">Password</label>
          <input id="auth-password" name="password" type="password" autocomplete="${registering ? "new-password" : "current-password"}" required minlength="12" maxlength="128" placeholder="At least 12 characters">
          ${registering ? `<p class="hint">Use at least 12 characters. A longer phrase is easier to remember.</p>` : ""}
          <button class="primary full-button" type="submit">${registering ? "Create account" : "Sign in"}</button>
        </form>
        <p class="auth-switch">${registering ? "Already have an account?" : "New to Field Shift?"}
          <button type="button" class="link" id="switch-auth">${registering ? "Sign in" : "Create an account"}</button>
        </p>
        <p><button class="link" id="forgot-password" type="button">Recover your account</button></p>
      </section>
      <section class="card">
        <h2 class="card-title">${icon("layers")} What a plan shows you</h2>
        <p class="muted">Your current crop and up to two other crops, compared on the same field and the same past seasons:</p>
        <ul class="sources-list">
          <li><strong>${icon("drop")} Water needs</strong>Typical irrigation need and rain-fed water gap per season.</li>
          <li><strong>${icon("roots")} Soil layers</strong>Root depth, the water the soil can hold, and recent NASA SMAP soil moisture.</li>
          <li><strong>${icon("sun")} Past-season spread</strong>How much the result moved from one season to the next.</li>
        </ul>
        <div class="privacy-card">${icon("shield")}<div><strong>Private by default</strong>Your fields and notes are visible only in your account. Location is used to find the nearest weather and soil records.</div></div>
      </section>
    </div>`;
  document.getElementById("switch-auth").onclick = () => renderAuth(registering ? "login" : "register");
  document.getElementById('forgot-password').onclick = recoverAccount;
  document.getElementById('guest-explore').onclick = () => renderFieldEditor();
  document.getElementById('guest-demo').onclick = runDemo;
  document.getElementById("auth-form").onsubmit = async (event) => {
    event.preventDefault();
    if (busy) return;
    busy = true;
    const button = event.currentTarget.querySelector("button[type=submit]");
    button.disabled = true;
    button.textContent = registering ? "Creating your account…" : "Signing in…";
    const data = new FormData(event.currentTarget);
    try {
      const result = await getJSON(`${API}/auth/${registering ? "register" : "login"}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: data.get("name"), email: data.get("email"), password: data.get("password") }),
      });
      user = result.user;
      authVersion++;
      busy = false;
      setHeader();
      if (result.recovery_code) showRecoveryCode(result.recovery_code);
      else await showHome();
    } catch (err) {
      busy = false;
      renderAuth(mode, err.message);
    }
  };
}

function showRecoveryCode(code) {
  setMapVisible(false);
  panel.innerHTML = `<section class="auth-wrap recovery-wrap">
    <div class="icon-bubble">Save this code</div>
    <h1>Keep your recovery code</h1>
    <p class="lead">This code is shown only once. Save it somewhere private so you can recover your account if you forget your password.</p>
    <div class="recovery-code" id="recovery-code">${esc(code)}</div>
    <button type="button" class="primary full-button" id="continue-home">I saved my code</button>
    <p class="hint">Field Shift does not email this code to you.</p>
  </section>`;
  document.getElementById("continue-home").onclick = () => showHome();
}

async function signOut() {
  try { await getJSON(`${API}/auth/logout`, { method: "POST" }); } catch (err) { return accountSettings(err.message); }
  user = null; fields = []; activeField = null; currentAnalysis = null; chatSession = null;
  authVersion++;busy=false;
  setHeader(); renderAuth("login");
}

async function loadFields(render, message = "") {
  if (!user) return renderAuth();
  const ownerVersion=authVersion;
  setMapVisible(false);
  busy = false;
  panel.innerHTML = skeleton();
  try {
    const result = await getJSON(`${API}/fields`);
    if(ownerVersion!==authVersion)return;
    fields = result.fields;
    render(message);
  } catch (err) {
    if(ownerVersion!==authVersion)return;
    if (err.status === 401) { user = null; setHeader(); return renderAuth("login"); }
    render(`We could not load your fields: ${err.message}`);
  }
}

async function showHome(message = "") {
  currentAnalysis = null;
  chatSession = null;
  return loadFields(renderHome, message);
}

async function showLands(message = "") { return loadFields(renderLands, message); }

function cropName(id) {
  const name = catalog.crops.find((crop) => crop.id === id)?.name;
  if (id === "maize_grain") return "Corn";
  return name || (id === "unknown" ? "Not sure yet" : id || "Not entered");
}

function plainCropName(crop) { return crop.id === "maize_grain" ? "Corn" : crop.name; }
function coverageLabel(status) {
  return ({ supported: "Available", partial: "Some records", unsupported: "Not available", unchecked: "Not checked yet", unknown: "Not checked" })[status] || "Not checked";
}

function renderHome(message = "") {
  setMapVisible(false);
  setTab("home");
  const firstName = (user?.name || "").trim().split(/\s+/)[0] || "there";
  panel.innerHTML = `
    <section class="home-hero">
      <div><p class="eyebrow">Your farm home · ${esc(firstName)}</p><h1>Plan your seasons around your field’s conditions</h1>
      <p class="lead">Add what you know about each field, then compare crop plans against 25 past seasons of NASA weather and USDA soil records.</p>
      ${fields.length ? `<div class="stat-row">${fields.slice(0, 4).map((field) => `<span class="stat-pill">${icon("pin")}<strong>${esc(field.name)}</strong>${esc(cropName(field.crop))}</span>`).join("")}</div>` : ""}</div>
      <div class="button-row"><button type="button" class="primary" id="add-field">${icon("plus")} Add a field</button><button type="button" class="secondary-button" id="home-demo">See a saved example</button></div>
    </section>
    ${message ? `<div class="notice-card" role="status">${esc(message)}</div>` : ""}
    <div class="home-grid">
      <article class="card"><h2 class="card-title">${icon("sprout")} Your land</h2>
        ${fields.length ? `<p><strong>${fields.length} saved field${fields.length === 1 ? "" : "s"}</strong></p><p class="muted">Compare plans, update details or remove a field.</p>` : `<p><strong>No fields yet</strong></p><p class="muted">Add your first field to compare crop plans for it.</p>`}
        <div class="button-row"><button type="button" class="secondary-button" id="home-lands">${fields.length ? "Open my land" : "Add a field"}</button></div></article>
      <article class="card"><h2 class="card-title">${icon("layers")} Your plans</h2><p class="muted">Every comparison keeps the source records, equations and assumptions used at the time.</p>
        <div class="button-row"><button type="button" class="secondary-button" id="home-plans">Open saved plans</button></div></article>
      <article class="card"><h2 class="card-title">${icon("note")} Field notes</h2><p class="muted">Keep private, dated notes and photos. Send one to an agronomist when you want a person’s view.</p>
        <div class="button-row"><button type="button" class="secondary-button" id="home-notes">Open field notes</button></div></article>
      <article class="tint-card"><h2 class="card-title">${icon("info")} Decisions start with evidence</h2><p>Plans replay past weather. They are not forecasts or irrigation prescriptions, and field accuracy has not been validated yet. Check them against local knowledge.</p><p><a href="/science/#validation">See the validation status</a></p></article>
    </div>`;
  document.getElementById("add-field").onclick = () => renderFieldEditor();
  document.getElementById("home-demo").onclick = runDemo;
  document.getElementById("home-lands").onclick = () => fields.length ? renderLands() : renderFieldEditor();
  document.getElementById("home-plans").onclick = () => { currentAnalysis = null; renderPlans(); };
  document.getElementById("home-notes").onclick = () => renderNotesHub();
}

function renderLands(message = "") {
  setMapVisible(false);
  setTab("land");
  panel.innerHTML = `
    <section class="journal-header"><div><p class="eyebrow">My land</p><h1>Your fields</h1><p class="lead">Choose a field to compare crop plans, update its details, or open its notes.</p></div>
      <button type="button" class="primary" id="add-field">${icon("plus")} Add a field</button></section>
    ${message ? `<div class="notice-card" role="status">${esc(message)}</div>` : ""}
    ${fields.length ? `<div class="field-grid">${fields.map((field) => fieldCard(field)).join("")}</div>`
      : stateCard("sprout", "Start with what you know about your field", "Its location, what you grow, and anything you know about the soil. You can answer “I don’t know” to any question.", `<button type="button" class="primary" id="empty-add">${icon("plus")} Add a field</button><button type="button" class="secondary-button" id="empty-demo">See a saved example</button>`)}`;
  document.getElementById("add-field").onclick = () => renderFieldEditor();
  document.getElementById("empty-add")?.addEventListener("click", () => renderFieldEditor());
  document.getElementById("empty-demo")?.addEventListener("click", runDemo);
  panel.querySelectorAll("[data-edit-field]").forEach((button) => button.onclick = () => renderFieldEditor(fields.find((field) => field.id === button.dataset.editField)));
  panel.querySelectorAll("[data-run-field]").forEach((button) => button.onclick = () => reviewComparison(fields.find((field) => field.id === button.dataset.runField),document.getElementById(`goal-${button.dataset.runField}`).value));
  panel.querySelectorAll('[data-delete-field]').forEach(button=>button.onclick=()=>deleteField(fields.find(field=>field.id===button.dataset.deleteField)));
  panel.querySelectorAll('[data-field-journal]').forEach(button=>button.onclick=()=>renderFieldObservations(fields.find(field=>field.id===button.dataset.fieldJournal)));
  panel.querySelectorAll('[data-field-note]').forEach(button=>button.onclick=()=>renderObservationForm(fields.find(field=>field.id===button.dataset.fieldNote)));
}

function fieldCard(field) {
  const detail=field.details||{};
  const rotation=(field.history||[]).filter(item=>item.crop&&item.crop!=='unknown').map(item=>`${item.year}: ${cropName(item.crop)}`).join(' · ');
  const goal=field.goal||'conserve_water';
  return `<article class="field-card">
    <div class="field-card-top"><span class="field-glyph">${icon("sprout")}</span><span class="state-pill">${esc(field.state)}</span></div>
    <h3>${esc(field.name)}</h3><p class="muted">Current crop · ${esc(cropName(field.crop))}</p>
    <p class="field-coords">${Number(field.lat).toFixed(3)}°, ${Number(field.lon).toFixed(3)}°</p>
    <div class="field-card-context">${detail.area_acres?`<span>${esc(detail.area_acres)} acres</span>`:""}<span>${field.irrigation==='rain-fed'?'Rain-fed':field.irrigation==='irrigated'?'Irrigated':'Water source not confirmed'}</span>${rotation?`<span>Recent crops · ${esc(rotation)}</span>`:""}${(detail.priorities||[]).map(p=>`<span>${esc(PRIORITIES[p]||p)}</span>`).join('')}</div>
    <label for="goal-${esc(field.id)}">Main priority</label><select id="goal-${esc(field.id)}">${Object.entries(GOALS).map(([key,label])=>`<option value="${key}"${key===goal?' selected':''}>${label}</option>`).join('')}</select><div class="field-card-actions"><button type="button" class="primary" data-run-field="${esc(field.id)}">Compare plans</button><button type="button" class="quiet-button" data-edit-field="${esc(field.id)}">Edit field</button><button type="button" class="quiet-button" data-delete-field="${esc(field.id)}">Remove</button></div>
    <div class="field-card-journal-actions"><button type="button" class="quiet-button" data-field-journal="${esc(field.id)}">${icon("note")} Field notes</button><button type="button" class="quiet-button" data-field-note="${esc(field.id)}">${icon("plus")} Add a note</button></div>
  </article>`;
}

async function reviewComparison(field,goal=field?.goal||'conserve_water') {
  if(!field)return;
  activeField={...field,goal};setMapVisible(true);setTab('plans');
  map?.flyTo({center:[field.lon,field.lat],zoom:Math.max(map.getZoom(),5.5),duration:500});putMarker(field.lat,field.lon);
  const ownerVersion=authVersion;
  const startYear=Math.max(2001,new Date().getFullYear()-25);
  const endYear=new Date().getFullYear()-1;
  const years=endYear-startYear+1;
  panel.innerHTML=`<div class="form-topline"><button type="button" class="back-link" id="review-back">← My fields</button><span class="step-label">REVIEW YOUR COMPARISON</span></div><p class="eyebrow">BEFORE WE RUN IT</p><h1>Check these field details</h1><p class="lead">A quick review helps make sure we’re comparing the right place and the right crop context.</p><section class="review-field-card"><div><span class="review-label">FIELD</span><h2>${esc(field.name)}</h2><p>${esc(field.state||'Location will be checked')} · ${Number(field.lat).toFixed(3)}°, ${Number(field.lon).toFixed(3)}°</p></div><div><span class="review-label">CURRENT CROP</span><strong>${esc(cropName(field.crop))}</strong><p>${field.irrigation==='rain-fed'?'Rain-fed':field.irrigation==='irrigated'?'Irrigated':'Water source not confirmed'}</p></div><div><span class="review-label">YOUR GOAL</span><strong>${esc(GOALS[goal]||goal)}</strong><p>${years} past seasons requested</p></div></section><div class="review-context"><h2>Field context you shared</h2>${field.history?.length?`<p><strong>Recent crops:</strong> ${esc(field.history.map(item=>`${item.year}: ${cropName(item.crop)}`).join(' · '))}</p>`:`<p>Crop history not added. You can still compare the supported options.</p>`}${field.details?.area_acres?`<p><strong>Approximate area:</strong> ${esc(field.details.area_acres)} acres</p>`:""}${field.details?.soil_texture&&field.details.soil_texture!=='unknown'?`<p><strong>Your soil description:</strong> ${esc(field.details.soil_texture)}</p>`:""}<p class="hint">Your observations add context; calculations use the mapped public soil record.</p></div><section class="review-data"><h2>Checking nearby data</h2><div id="review-coverage" class="review-data-grid"><span class="chip">NASA weather · Checking…</span><span class="chip">USDA soil · Checking…</span></div><p class="small muted">The comparison replays past weather with crop and mapped soil assumptions. It is a research estimate, not a forecast or a field irrigation prescription.</p></section><div class="form-actions"><button type="button" class="primary" id="run-reviewed-analysis">Run this comparison</button><button type="button" class="quiet-button" id="edit-reviewed-field">Edit field details</button></div>`;
  document.getElementById('review-back').onclick=()=>user?showHome():renderFieldEditor(field);
  document.getElementById('edit-reviewed-field').onclick=()=>renderFieldEditor(field);
  document.getElementById('run-reviewed-analysis').onclick=()=>startAnalysis(activeField,goal);
  try{
    const data=await getJSON(`${API}/coverage`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({lat:field.lat,lon:field.lon,mode:'live'})});
    if(ownerVersion!==authVersion)return;
    const weather=data.products?.nasa_power?.status||'unknown',soil=data.products?.ssurgo?.status||'unknown';
    const target=document.getElementById('review-coverage');if(!target)return;
    target.innerHTML=`<span class="chip ${esc(weather)}">NASA weather · ${esc(coverageLabel(weather))}</span><span class="chip ${esc(soil)}">USDA soil · ${esc(coverageLabel(soil))}</span>`;
    if(data.products?.ssurgo?.label)target.insertAdjacentHTML('afterend',`<p class="small muted">Nearby mapped soil: ${esc(data.products.ssurgo.label)} · not a field test</p>`);
    if(!data.in_scope){document.getElementById('run-reviewed-analysis').disabled=true;target.insertAdjacentHTML('afterend','<p class="errors">This location is outside the current U.S. coverage.</p>');}
  }catch{const target=document.getElementById('review-coverage');if(target)target.innerHTML='<span class="chip unknown">NASA weather · Not checked</span><span class="chip unknown">USDA soil · Not checked</span><p class="small">We could not check sources now. You can still run the comparison and review its data status in the results.</p>';}
}

const OBSERVATION_CATEGORIES={water:'Water concern',pest_disease:'Pest or disease concern',growth:'Crop growth',weather:'Weather damage',other:'Other observation'};
let observationPreviewUrl=null;

function clearObservationPreview(){if(observationPreviewUrl){URL.revokeObjectURL(observationPreviewUrl);observationPreviewUrl=null;}}

async function renderFieldObservations(field,message=''){
  if(!user)return renderAuth('login','Sign in to keep a private field journal.');
  if(!field)return showHome();
  setMapVisible(false);setTab('notes');panel.innerHTML=skeleton();
  try{
    const data=await getJSON(`${API}/fields/${encodeURIComponent(field.id)}/observations`);
    panel.innerHTML=`<div class="form-topline"><button type="button" class="back-link" id="journal-home">← My fields</button><span class="step-label">PRIVATE FIELD JOURNAL</span></div><section class="journal-header"><div><p class="eyebrow">${esc(field.state||'FIELD NOTES')}</p><h1>${esc(field.name)}</h1><p class="lead">Keep dated observations in one place. Notes and photos stay private until you choose to share one with an agronomist.</p></div><button class="primary" id="add-observation">＋ Add field note</button></section>${message?`<div class="notice-card" role="status">${esc(message)}</div>`:''}<div class="journal-privacy"><strong>Private by default</strong><span>Notes are not published as local alerts. An expert only sees a note when you send it with a question.</span></div>${data.observations.length?`<div class="observation-list">${data.observations.map(observationCard).join('')}</div>`:`<section class="empty-state"><div class="empty-illustration">✎</div><h2>No field notes yet</h2><p>Record what you notice after rain, during crop growth, or when something changes in the field.</p><button class="primary" id="empty-observation">Add your first note</button></section>`}`;
    document.getElementById('journal-home').onclick=()=>renderNotesHub();
    document.getElementById('add-observation').onclick=()=>renderObservationForm(field);
    document.getElementById('empty-observation')?.addEventListener('click',()=>renderObservationForm(field));
    panel.querySelectorAll('[data-ask-observation]').forEach(button=>button.onclick=()=>renderExpertRequest(null,field,data.observations.find(item=>item.id===button.dataset.askObservation)));
    panel.querySelectorAll('[data-delete-observation]').forEach(button=>button.onclick=async()=>{
      if(!window.confirm('Delete this private field note and its photo?'))return;
      try{await getJSON(`${API}/fields/${encodeURIComponent(field.id)}/observations/${encodeURIComponent(button.dataset.deleteObservation)}`,{method:'DELETE'});await renderFieldObservations(field,'Field note deleted.');}
      catch(error){await renderFieldObservations(field,error.message);}
    });
  }catch(error){panel.innerHTML=`<div class="form-topline"><button class="back-link" id="journal-home">← My fields</button></div><h1>Field journal unavailable</h1><p class="errors">${esc(error.message)}</p>`;document.getElementById('journal-home').onclick=()=>renderNotesHub();}
}

function observationCard(item){
  const state=item.expert_status==='open'?'Waiting for expert':item.expert_status==='replied'?'Expert replied':'Private · not shared';
  return `<article class="observation-card"><div class="observation-card-head"><div><span class="state-pill">${esc(state)}</span><span class="state-pill">${esc(OBSERVATION_CATEGORIES[item.category]||'Field note')}</span></div><time datetime="${esc(item.observed_on)}">${esc(new Date(`${item.observed_on}T12:00:00`).toLocaleDateString())}</time></div><h2>${esc(cropName(item.crop))}</h2><p class="observation-note">${esc(item.note)}</p>${item.photo_url?`<img class="observation-photo" src="${esc(item.photo_url)}" alt="Photo attached to this private field note" loading="lazy">`:''}<div class="observation-actions">${item.expert_status==='replied'?'<span class="hint">Open Expert replies to see the answer.</span>':`<button type="button" class="secondary-button" data-ask-observation="${esc(item.id)}">Ask an agronomist about this note</button>`}<button type="button" class="quiet-button" data-delete-observation="${esc(item.id)}">Delete note</button></div></article>`;
}

function renderObservationForm(field,error=''){
  if(!user)return renderAuth('login','Sign in to save a private field note.');
  clearObservationPreview();
  setMapVisible(false);setTab('notes');
  const now=new Date(),localToday=new Date(now.getTime()-now.getTimezoneOffset()*60000).toISOString().slice(0,10);
  panel.innerHTML=`<div class="form-topline"><button class="back-link" id="observation-back">← Field journal</button><span class="step-label">PRIVATE FIELD NOTE</span></div><section class="expert-request-card"><p class="eyebrow">WHAT DID YOU NOTICE?</p><h1>Add a field note</h1><p class="lead">A dated note helps you track what changed in your field and gives an agronomist useful context if you choose to ask.</p>${error?`<div class="errors" role="alert">${esc(error)}</div>`:''}<div class="notice-card"><strong>${esc(field.name)}</strong> · ${esc(field.state||'Saved field')}</div><form id="observation-form"><label for="observation-date">When did you notice it?</label><input id="observation-date" name="observed_on" type="date" value="${localToday}" max="${localToday}" required><label for="observation-crop">Crop</label><select id="observation-crop" name="crop">${cropSelectOptions(field.crop||'unknown')}</select><label for="observation-category">What is the note about?</label><select id="observation-category" name="category">${Object.entries(OBSERVATION_CATEGORIES).map(([value,label])=>`<option value="${value}">${label}</option>`).join('')}</select><label for="observation-note">What did you notice?</label><textarea id="observation-note" name="note" rows="4" minlength="5" maxlength="2000" required placeholder="For example, water is standing in the low area after yesterday’s rain."></textarea><label for="observation-photo">Add a photo <span class="hint">Optional</span></label><input id="observation-photo" name="photo" type="file" accept="image/*" capture="environment"><div id="observation-preview" class="observation-preview" hidden></div><p class="hint">Photos are resized and location metadata is removed. Avoid including people or private documents.</p><div class="form-actions"><button class="primary" type="submit">Save private note</button><button class="quiet-button" type="button" id="observation-cancel">Cancel</button></div><p class="hint">This note stays in your account. It is shared with an agronomist only if you choose “Ask an agronomist about this note.”</p></form></section>`;
  document.getElementById('observation-back').onclick=()=>{clearObservationPreview();renderFieldObservations(field);};
  document.getElementById('observation-cancel').onclick=()=>{clearObservationPreview();renderFieldObservations(field);};
  document.getElementById('observation-photo').onchange=event=>{
    const file=event.target.files?.[0],preview=document.getElementById('observation-preview');
    if(!preview)return;clearObservationPreview();preview.replaceChildren();preview.hidden=!file;
    if(file){const image=document.createElement('img');image.alt='Preview of the selected field photo';observationPreviewUrl=URL.createObjectURL(file);image.src=observationPreviewUrl;preview.append(image);}
  };
  document.getElementById('observation-form').onsubmit=async event=>{
    event.preventDefault();const form=event.currentTarget,button=form.querySelector('button[type=submit]');button.disabled=true;button.textContent='Saving…';
    try{
      const data=new FormData(form),file=data.get('photo');
      const photo_data=file?.size?await observationPhotoBase64(file):null;
      await getJSON(`${API}/fields/${encodeURIComponent(field.id)}/observations`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({observed_on:data.get('observed_on'),crop:data.get('crop'),category:data.get('category'),note:data.get('note'),photo_data})});
      clearObservationPreview();
      await renderFieldObservations(field,'Your note was saved privately. It has not been shared.');
    }catch(err){button.disabled=false;button.textContent='Save private note';const target=document.querySelector('#observation-form .errors')||document.createElement('div');target.className='errors';target.setAttribute('role','alert');target.textContent=err.message;if(!target.isConnected)form.prepend(target);}
  };
}

async function observationPhotoBase64(file){
  if(file.size>12_000_000)throw new Error('Choose a photo smaller than 12 MB.');
  const bitmap=await createImageBitmap(file);const scale=Math.min(1,1600/Math.max(bitmap.width,bitmap.height));
  const canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.round(bitmap.width*scale));canvas.height=Math.max(1,Math.round(bitmap.height*scale));
  canvas.getContext('2d').drawImage(bitmap,0,0,canvas.width,canvas.height);bitmap.close?.();
  const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/jpeg',0.82));if(!blob)throw new Error('This photo could not be prepared. Choose another image.');
  return await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',',2)[1]);reader.onerror=()=>reject(new Error('This photo could not be read.'));reader.readAsDataURL(blob);});
}

function cropSelectOptions(selected) {
  return `<option value="unknown"${selected === "unknown" ? " selected" : ""}>I’m not sure</option>` +
    catalog.crops.map((crop) => `<option value="${esc(crop.id)}"${selected === crop.id ? " selected" : ""}>${esc(plainCropName(crop))}</option>`).join("");
}

function yearsForHistory(history = []) {
  const currentYear = new Date().getFullYear();
  return [currentYear - 2, currentYear - 1].map((year) => ({ year, crop: history.find((item) => item.year === year)?.crop || "unknown" }));
}

const WIZARD_STEPS = ["Location", "Crops and water", "Soil", "Priorities"];

function renderFieldEditor(field = null, error = "", step = 1) {
  activeField = field;
  setMapVisible(true);
  setTab("land");
  const history = yearsForHistory(field?.history || []);
  const details = field?.details || {};
  const priorities = details.priorities || [];
  panel.innerHTML = `
    <div class="form-topline"><button type="button" class="back-link" id="back-home">${icon("back")} ${user ? "My land" : "Home"}</button><span class="step-label">${field?.id ? "Update field" : "Add a field"}</span></div>
    <div class="wizard-progress"><div class="wizard-progress-top"><span id="wizard-count">Step ${step} of 4</span><span id="wizard-name">${WIZARD_STEPS[step - 1]}</span></div><div class="wizard-bars" aria-hidden="true">${WIZARD_STEPS.map((_, i) => `<i class="${i < step ? "done" : ""}"></i>`).join("")}</div></div>
    <div id="wizard-error">${error ? errorBanner("We couldn’t save this field", error) : ""}</div>
    <form id="field-form" class="field-form" novalidate>
      <section class="wizard-step" data-step="1" aria-labelledby="step-1-title">
        <h1 id="step-1-title" tabindex="-1">Where is your field?</h1>
        <p class="lead">Its location picks the nearest NASA weather cell and the mapped USDA soil record. Click the map or type coordinates.</p>
        <label for="field-name">Field name <span aria-hidden="true">*</span></label>
        <input id="field-name" name="name" type="text" maxlength="80" required value="${esc(field?.name || "")}" placeholder="For example, North field" aria-describedby="field-name-error">
        <p class="field-error" id="field-name-error" hidden>${icon("alert")} Add a name so you can tell your fields apart, for example “North field”.</p>
        <div class="row coordinate-row">
          <div><label for="lat">Latitude</label><input id="lat" name="lat" type="number" inputmode="decimal" step="any" required value="${field ? esc(field.lat) : ""}" placeholder="38.85" aria-describedby="coord-error"></div>
          <div><label for="lon">Longitude</label><input id="lon" name="lon" type="number" inputmode="decimal" step="any" required value="${field ? esc(field.lon) : ""}" placeholder="-99.33" aria-describedby="coord-error"></div>
        </div>
        <p class="field-error" id="coord-error" hidden>${icon("alert")} Choose a point on the map, or enter a latitude between −90 and 90 and a longitude between −180 and 180.</p>
        <button type="button" id="check-location" class="secondary-button full-width">${icon("pin")} Check this location</button>
        <div id="location-result" class="location-result" aria-live="polite">${field?.state ? `<p class="muted small">Saved location: ${esc(field.state)}</p>` : `<p class="muted small">Select a point on the map. We’ll check which weather and soil records cover it.</p>`}</div>
        <label for="area-acres">Approximate size <span class="hint">optional</span></label><div class="unit-input"><input id="area-acres" name="area_acres" type="number" min="0.01" step="any" value="${esc(details.area_acres ?? "")}" placeholder="For example, 40"><span>acres</span></div>
        <div class="privacy-card">${icon("shield")}<div><strong>Your location stays private</strong>Saved fields are visible only in your account. Plans show the location rounded to 0.1°, about 10 km.</div></div>
      </section>
      <section class="wizard-step" data-step="2" aria-labelledby="step-2-title" hidden>
        <h1 id="step-2-title" tabindex="-1">What do you grow?</h1>
        <p class="lead">Your current crop is the plan the others are compared with. Past crops describe the rotation.</p>
        <div class="card wizard-summary" id="wizard-summary"></div>
        <label for="current-crop">Current crop</label>
        <select id="current-crop" name="crop">${cropSelectOptions(field?.crop || "unknown")}</select>
        <fieldset class="fieldset-card"><legend>${icon("layers")} Previous crops <span class="hint">optional</span></legend>
          ${history.map((item, index) => `<label for="history-${index}">Crop in ${item.year}</label><select id="history-${index}" name="history-${item.year}">${cropSelectOptions(item.crop)}</select>`).join("")}
          <p class="hint">Choose “I’m not sure” if you don’t remember. The rotation note uses this; the water results don’t.</p>
        </fieldset>
        <fieldset class="choice-group"><legend>How does the field get water?</legend>
          ${[["rain-fed", "Rain only"], ["irrigated", "Irrigation"], ["unknown", "I don’t know"]].map(([value, text]) => `<label class="choice-card"><input type="radio" name="irrigation" value="${value}"${(field?.irrigation || "unknown") === value ? " checked" : ""}><span>${text}</span></label>`).join("")}
        </fieldset>
        <label for="water-source">Where does irrigation water come from?</label><select id="water-source" name="water_source">${selectOptions(WATER_SOURCES, details.water_source || "unknown")}</select>
      </section>
      <section class="wizard-step" data-step="3" aria-labelledby="step-3-title" hidden>
        <h1 id="step-3-title" tabindex="-1">What do you know about the soil?</h1>
        <p class="lead">“I don’t know” is a fine answer. Your answers help you and an agronomist check the mapped soil record.</p>
        <div class="fieldset-card"><h2>${icon("soil")} Soil details</h2>
          <label for="soil-texture">What does the soil feel like?</label><select id="soil-texture" name="soil_texture">${selectOptions(SOIL_TEXTURES, details.soil_texture || "unknown")}</select>
          <label for="soil-test">Do you have a soil test?</label><select id="soil-test" name="soil_test">${selectOptions(SOIL_TESTS, details.soil_test || "unknown")}</select>
          <label for="drainage">How quickly does water drain after rain?</label><select id="drainage" name="drainage">${selectOptions(DRAINAGE, details.drainage || "unknown")}</select>
          <label for="slope">How would you describe the slope?</label><select id="slope" name="slope">${selectOptions(SLOPES, details.slope || "unknown")}</select>
        </div>
        <div class="warn-card">${icon("alert")}<div><strong>The water calculation uses the mapped USDA soil</strong>Soil water storage comes from the USDA SSURGO record at this point, not from these answers. If what you see in the field is different, the plan will show both so you can raise it with an agronomist.</div></div>
      </section>
      <section class="wizard-step" data-step="4" aria-labelledby="step-4-title" hidden>
        <h1 id="step-4-title" tabindex="-1">What matters most this season?</h1>
        <p class="lead">Your main priority decides which water result leads the comparison.</p>
        <label for="field-goal">Main priority</label><select id="field-goal" name="goal">${Object.entries(GOALS).map(([key, label]) => `<option value="${key}"${(field?.goal || "conserve_water") === key ? " selected" : ""}>${label}</option>`).join("")}</select>
        <fieldset class="fieldset-card"><legend>Other priorities <span class="hint">choose any</span></legend><div class="check-chips">
          ${Object.entries(PRIORITIES).map(([key, label]) => `<label class="check-chip"><input type="checkbox" name="priorities" value="${key}"${priorities.includes(key) ? " checked" : ""}>${label}</label>`).join("")}
        </div></fieldset>
        <div class="fieldset-card"><h2>What limits do you need to plan around?</h2>
          <label for="budget">Budget for changes</label><select id="budget" name="budget">${selectOptions(LEVELS, details.budget || "unknown")}</select>
          <label for="equipment">Equipment for a different crop</label><select id="equipment" name="equipment">${selectOptions(LEVELS, details.equipment || "unknown")}</select>
          <label for="marketing">Places to sell a different crop</label><select id="marketing" name="marketing">${selectOptions(LEVELS, details.marketing || "unknown")}</select>
        </div>
        <label for="field-notes">Anything else an agronomist should know? <span class="hint">optional</span></label><textarea id="field-notes" name="notes" maxlength="500" rows="3" placeholder="For example, a low spot stays wet after storms.">${esc(details.notes || "")}</textarea>
        <p class="hint">Priorities and limits stay with your field for your own review and for an agronomist. They don’t change the water calculation.</p>
      </section>
      <div class="wizard-nav"><button type="submit" class="primary" id="save-field">Save and continue ${icon("arrow")}</button><button type="button" class="secondary-button" id="wizard-back">Cancel</button></div>
      <p class="hint">${user ? "Field details are saved privately to your account." : "You’re exploring without an account. Sign in to keep this field across devices."}</p>
    </form>`;
  const form = document.getElementById("field-form");
  let current = 1;
  const show = (n, focus = true) => {
    current = n;
    form.querySelectorAll(".wizard-step").forEach((section) => { section.hidden = Number(section.dataset.step) !== n; });
    document.getElementById("wizard-count").textContent = `Step ${n} of 4`;
    document.getElementById("wizard-name").textContent = WIZARD_STEPS[n - 1];
    panel.querySelectorAll(".wizard-bars i").forEach((bar, i) => bar.classList.toggle("done", i < n));
    document.getElementById("save-field").innerHTML = n < 4 ? `Save and continue ${icon("arrow")}` : `${user ? "Save and review" : "Review my plans"} ${icon("arrow")}`;
    document.getElementById("wizard-back").textContent = n === 1 ? "Cancel" : `Back to ${WIZARD_STEPS[n - 2].toLowerCase()}`;
    if (n === 2) {
      const name = document.getElementById("field-name").value.trim(), lat = document.getElementById("lat").value, lon = document.getElementById("lon").value;
      const size = document.getElementById("area-acres").value;
      document.getElementById("wizard-summary").innerHTML = `<h2>${icon("sprout")} ${esc(name)}</h2><p>${esc(Number(lat).toFixed(3))}°, ${esc(Number(lon).toFixed(3))}°${size ? ` · ${esc(size)} acres` : ""}</p><span class="done-chip">${icon("check")} Location saved for this step</span>`;
    }
    if (focus) document.getElementById(`step-${n}-title`)?.focus();
  };
  const markInvalid = (input, errorId, bad) => { input.setAttribute("aria-invalid", String(bad)); document.getElementById(errorId).hidden = !bad; };
  const validateLocation = () => {
    const name = document.getElementById("field-name"), lat = document.getElementById("lat"), lon = document.getElementById("lon");
    const latValue = Number(lat.value), lonValue = Number(lon.value);
    const nameBad = !name.value.trim();
    const coordBad = lat.value === "" || lon.value === "" || !(latValue >= -90 && latValue <= 90) || !(lonValue >= -180 && lonValue <= 180);
    markInvalid(name, "field-name-error", nameBad);
    markInvalid(lat, "coord-error", coordBad); lon.setAttribute("aria-invalid", String(coordBad));
    document.getElementById("wizard-error").innerHTML = nameBad || coordBad ? errorBanner("This step isn’t finished", nameBad ? "The field name is empty. Add a name below, then choose “Save and continue”." : "The location is missing or out of range. Click the map or check the coordinates.") : "";
    if (nameBad) name.focus(); else if (coordBad) lat.focus();
    return !nameBad && !coordBad;
  };
  form.onsubmit = (event) => {
    if (current === 1 && !validateLocation()) { event.preventDefault(); return; }
    if (current < 4) { event.preventDefault(); show(current + 1); return; }
    if (!validateLocation()) { event.preventDefault(); show(1, false); return; }
    return saveField(event);
  };
  document.getElementById("wizard-back").onclick = () => current > 1 ? show(current - 1) : (user ? showLands() : renderAuth());
  document.getElementById("back-home").onclick = () => user ? showLands() : renderAuth();
  document.getElementById("check-location").onclick = () => {
    const lat = Number(document.getElementById("lat").value), lon = Number(document.getElementById("lon").value);
    if (Number.isFinite(lat) && Number.isFinite(lon) && document.getElementById("lat").value) chooseLocation(lat, lon);
    else document.getElementById("location-result").innerHTML = `<p class="error">Enter both latitude and longitude, or click the map.</p>`;
  };
  show(step, false);
  if (field) {
    map?.setCenter([field.lon, field.lat]); map?.setZoom(5); putMarker(field.lat, field.lon);
  } else {
    map?.fitBounds(VIEWS.lower48, { padding: 24 });
  }
}

async function chooseLocation(lat, lon) {
  if (lat < -90 || lat > 90 || lon < -180 || lon > 180) return;
  const token = ++fieldLocationToken;
  const latitude = document.getElementById("lat"), longitude = document.getElementById("lon");
  if (latitude) latitude.value = lat;
  if (longitude) longitude.value = lon;
  putMarker(lat, lon);
  const target = document.getElementById("location-result");
  if (!target) return;
  target.innerHTML = `<p class="muted small" aria-live="polite">Checking nearby records…</p>`;
  try {
    const result = await getJSON(`${API}/coverage`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ lat, lon, mode: "live" }) });
    if (token !== fieldLocationToken) return;
    if (!result.in_scope) target.innerHTML = `<p class="error">This location is outside the areas currently covered. Choose a point in one of the 50 U.S. states.</p>`;
    else {
      const weather = result.products?.nasa_power?.status || "unknown";
      const soil = result.products?.ssurgo?.status || "unknown";
      const soilText = result.products?.ssurgo?.label ? `<p class="small muted">Nearby soil record: ${esc(result.products.ssurgo.label)}</p>` : "";
      target.innerHTML = `<p><strong>${esc(result.state.name)}</strong></p><div class="chips"><span class="chip ${esc(weather)}">Nearby weather: ${esc(coverageLabel(weather))}</span><span class="chip ${esc(soil)}">Nearby soil: ${esc(coverageLabel(soil))}</span></div>${soilText}`;
    }
  } catch (err) {
    if (token === fieldLocationToken) target.innerHTML = `<p class="error">We couldn’t check records just now. You can still save the location and try again later.</p>`;
  }
}

async function saveField(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const data = new FormData(form);
  const body = {
    name: data.get("name"), lat: Number(data.get("lat")), lon: Number(data.get("lon")),
    crop: data.get("crop"), irrigation: data.get("irrigation"),
    area_acres: data.get("area_acres") ? Number(data.get("area_acres")) : null,
    soil_texture: data.get("soil_texture"), drainage: data.get("drainage"), slope: data.get("slope"),
    water_source: data.get("water_source"), notes: data.get("notes") || "",
    soil_test: data.get("soil_test") || "unknown", priorities: data.getAll("priorities"),
    budget: data.get("budget") || "unknown", equipment: data.get("equipment") || "unknown", marketing: data.get("marketing") || "unknown",
    history: yearsForHistory(activeField?.history || []).map(({ year }) => ({ year, crop: data.get(`history-${year}`) })),
  };
  const details = Object.fromEntries(["area_acres", "soil_texture", "drainage", "slope", "water_source", "notes", "soil_test", "priorities", "budget", "equipment", "marketing"].map((key) => [key, body[key]]));
  const button = document.getElementById("save-field");
  if (!user) {
    activeField={...body,details,goal:data.get('goal')};
    return reviewComparison(activeField,data.get('goal'));
  }
  button.disabled = true; button.textContent = "Saving…";
  try {
    const saved=await getJSON(activeField?.id ? `${API}/fields/${encodeURIComponent(activeField.id)}` : `${API}/fields`, {
      method: activeField?.id ? "PUT" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    const nextField={...body,id:saved.id||activeField?.id,state:saved.state||activeField?.state,details,goal:data.get('goal')};
    activeField=nextField;
    await reviewComparison(nextField,data.get('goal'));
  } catch (err) {
    button.disabled = false; button.textContent = "Save and review";
    const target = document.getElementById("wizard-error");
    if (target) { target.innerHTML = errorBanner("We couldn’t save this field", err.message); target.scrollIntoView({ block: "center" }); }
  }
}

async function startAnalysis(field, goal = field?.goal || "conserve_water", mode = "live") {
  if (!field || busy) return;
  busy = true;
  const ownerVersion=authVersion;
  currentAnalysis = null; chatSession = null;
  setMapVisible(false);
  const currentYear = new Date().getFullYear();
  const candidates = catalog.crops.map((crop) => crop.id);
  if (field.crop !== "unknown" && candidates.includes(field.crop)) candidates.sort((a, b) => (a === field.crop ? -1 : b === field.crop ? 1 : 0));
  const stageOrder = [["retrieving_weather", "Finding past NASA weather"], ["retrieving_soil", "Reading the USDA soil record"], ["simulating", "Running the water balance for each crop"], ["saving", "Preparing your plans"]];
  panel.innerHTML = `<section class="state-card" aria-busy="true"><span class="spinner-ring" aria-hidden="true"></span><p class="eyebrow">Preparing plans · ${esc(field.name)}</p><h1>Comparing past seasons</h1><p id="analysis-stage" aria-live="polite">Getting the request ready…</p><ol class="stage-list" id="analysis-stages">${stageOrder.map(([, label]) => `<li>${label}</li>`).join("")}</ol><p class="hint">Each crop is replayed through the same past seasons. This can take a minute.</p></section>`;
  try {
    const body = {
      mode, lat: field.lat, lon: field.lon, field_id: field.id,
      start_year: Math.max(2001, currentYear - 25), end_year: currentYear - 1,
      decision_year: currentYear, goal, irrigation: field.irrigation,
      history: (field.history || []).map((item) => ({ year: item.year, crop: item.crop, provenance: "farmer" })),
      current_practice: field.crop === "unknown" ? null : field.crop, candidates,
    };
    const job = await getJSON(`${API}/analyses`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const stages = { queued: "Waiting to start…", retrieving_weather: "Finding past weather…", retrieving_soil: "Checking soil information…", simulating: "Comparing crop choices…", saving: "Preparing your results…" };
    while (true) {
      const status = await getJSON(job.status_url);
      if(ownerVersion!==authVersion)return;
      const stage = document.getElementById("analysis-stage");
      if (stage) stage.textContent = stages[status.stage] || "Working on your comparison…";
      const reached = stageOrder.findIndex(([key]) => key === status.stage);
      document.getElementById("analysis-stages")?.querySelectorAll?.("li")?.forEach((item, index) => {
        item.className = index < reached || status.state === "succeeded" ? "done" : index === reached ? "active" : "";
      });
      if (status.state === "succeeded") {
        currentAnalysis = await getJSON(status.analysis_url);
        if(ownerVersion!==authVersion)return;
        busy = false;
        renderAnalysis(currentAnalysis, field);
        return;
      }
      if (status.state === "failed") throw new Error(status.error?.message || "The comparison could not be completed.");
      await new Promise((resolve) => setTimeout(resolve, 900));
    }
  } catch (err) {
    if(ownerVersion!==authVersion)return;
    busy = false;
    panel.innerHTML = `<section class="state-card error" role="alert"><span class="state-icon"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 3l18 18M8.5 8.6A5 5 0 0 0 12 17h6a3.5 3.5 0 0 0 1.6-6.6M16.4 7.4A6 6 0 0 0 6.1 9.2"/></svg></span><p class="eyebrow">Plans for ${esc(field.name)}</p><h1>We couldn’t get the data</h1><p>${esc(err.message)}</p><p class="hint">NASA and USDA services are sometimes busy, and records aren’t available everywhere. Your field details are kept.</p><div class="button-row"><button type="button" class="primary" id="analysis-retry">Try again</button><button type="button" class="secondary-button" id="analysis-home">${mode === "sample" ? "Back to home" : "Review field details"}</button></div></section>`;
    document.getElementById("analysis-retry").onclick = () => startAnalysis(field, goal, mode);
    document.getElementById("analysis-home").onclick = () => mode === "sample" ? showHome() : renderFieldEditor(field);
  }
}

function metricValue(strategy, key) {
  const metric = strategy?.result?.summary?.[key];
  const spread = metric?.spread;
  return spread ? `${Number(spread.median).toLocaleString(undefined, { maximumFractionDigits: 1 })} ${metric.unit}` : "Not available";
}

function farmerWaterDepth(mm) {
  const value = Number(mm);
  if (!Number.isFinite(value)) return "not available";
  return `${(value / 25.4).toLocaleString(undefined, { maximumFractionDigits: 1 })} in (${value.toLocaleString(undefined, { maximumFractionDigits: 1 })} mm)`;
}

function exposureLevelLabel(level) {
  return ({ lower: "Lower than these options", middle: "Between these options", higher: "Higher than these options",
    similar: "Similar across options", insufficient_data: "Not enough data" })[level] || "Not assessed";
}

const LEVEL_TEXT = { limited: "limited", moderate: "some", adequate: "enough" };

// One plan card per strategy. Every number is a backend value; the meter shows the backend's
// relative water-gap score (0–100) and nothing else.
function planCard(strategy, index, context) {
  const { field, lowest, metricKey } = context;
  const label = (s) => s.crop === "maize_grain" ? "Corn" : s.name.replace(/\s*\(.*\)$/, "");
  const isCurrent = strategy.role === "current_practice";
  const alternatives = context.alternatives;
  const title = isCurrent ? "Current plan" : `Option ${alternatives.indexOf(strategy) + 1}`;
  const lastSeason = [...(field.history || [])].filter((item) => item.crop && item.crop !== "unknown").sort((a, b) => b.year - a.year)[0];
  const previous = lastSeason ? cropName(lastSeason.crop) : field.crop && field.crop !== "unknown" ? cropName(field.crop) : "Not entered";
  const previousLabel = lastSeason ? `Last season · ${lastSeason.year}` : "Now";
  const risk = strategy.water_stress_exposure || {};
  const pct = risk.percentage;
  const r = strategy.result;
  const rotation = strategy.rotation?.text;
  return `<article class="plan-card ${isCurrent ? "current" : ""}">
    <div class="plan-card-head"><div><h3>${esc(title)}</h3><p>${isCurrent ? "Keep what you grow now" : "Another crop for the same field"}</p></div>
      ${lowest === strategy ? `<span class="tag best">${icon("drop")} Smallest water gap</span>` : `<span class="tag">${esc(r ? `${r.seasons_simulated} seasons` : "No result")}</span>`}</div>
    <div class="sequence" aria-label="${esc(previous)} then ${esc(label(strategy))}"><div><span>${esc(previousLabel)}</span><strong>${esc(previous)}</strong></div>${icon("arrow")}<div class="next"><span>Next season</span><strong>${esc(label(strategy))}</strong></div></div>
    <div class="plan-rows">
      <div class="plan-row">${icon("drop")}<div><h4>Water needs</h4><p>Irrigation need <span class="value">${esc(metricValue(strategy, "irrigated_net_irrigation"))}</span>${r?.summary?.irrigated_net_irrigation?.spread ? ` · about ${esc(farmerWaterDepth(r.summary.irrigated_net_irrigation.spread.median).split(" (")[0])}` : ""}</p><p>Rain-fed water gap <span class="value">${esc(metricValue(strategy, "rainfed_deficit"))}</span></p><p class="hint">Medians of past seasons${metricKey === "rainfed_deficit" ? " · your priority leads with the water gap" : " · your priority leads with irrigation need"}.</p></div></div>
      <div class="plan-row">${icon("sun")}<div><h4>Water-stress exposure</h4><p><span class="value">${pct == null ? "Not assessed" : `${esc(Number(pct).toLocaleString(undefined, { maximumFractionDigits: 1 }))}%`}</span> relative water-gap score · ${esc(exposureLevelLabel(risk.relative_level))}</p>${pct == null ? "" : `<div class="meter" role="img" aria-label="Relative water-gap score ${esc(pct)} out of 100"><i style="width:${Math.max(0, Math.min(100, Number(pct) || 0))}%"></i></div>`}<p>${esc(risk.seasons_affected ?? 0)} of ${esc(risk.seasons_assessed ?? 0)} seasons had at least one modeled stress day.</p></div></div>
      <div class="plan-row">${icon("roots")}<div><h4>Soil and roots</h4><p>Roots reach <span class="value">${r?.root_depth_m != null ? `${esc(r.root_depth_m)} m` : "—"}</span>; the soil there holds <span class="value">${r?.taw_mm != null ? `${esc(Number(r.taw_mm).toLocaleString(undefined, { maximumFractionDigits: 1 }))} mm` : "—"}</span> of usable water.</p></div></div>
      <div class="plan-row">${icon("layers")}<div><h4>Rotation note</h4><p>${esc(rotation || "No rotation note for this crop sequence.")}</p>${strategy.rotation?.review_state ? `<p class="hint">Note status: ${esc(String(strategy.rotation.review_state).replaceAll("-", " "))}</p>` : ""}</div></div>
    </div>
    <details><summary>Reasons and details</summary><p>${esc(strategy.why_included || "")}</p><p>Planting date used: ${esc(strategy.planting || "—")} · valid past seasons: ${esc(r?.seasons_simulated ?? 0)}${r?.seasons_excluded?.length ? ` · excluded: ${esc(r.seasons_excluded.length)}` : ""}</p><p>Past variability is not a forecast confidence interval.</p></details>
  </article>`;
}

function renderAnalysis(result, field) {
  field = field || {name:result.location.state_name,crop:'unknown',lat:result.location.public_location.lat,lon:result.location.public_location.lon,history:[],irrigation:'unknown'};
  activeField = field;
  setMapVisible(true);
  setTab("plans", result.mode === "sample");
  document.body.classList.add("wide-results"); // map becomes a banner; plans get the full page width
  map?.flyTo({ center: [field.lon, field.lat], zoom: Math.max(map.getZoom(), 5.5), duration: 700 });
  putMarker(field.lat, field.lon);
  const metricKey = result.goal === "reduce_drought_stress" ? "rainfed_deficit" : "irrigated_net_irrigation";
  const mapSelection=mapLayersReady.then(layers=>layers?.selectAnalysisLayer(result.strategies[0]?.crop,metricKey)).catch(()=>null);
  const deficitFor = (strategy) => strategy.water_stress_exposure?.median_rainfed_deficit_mm
    ?? strategy.result?.summary?.rainfed_deficit?.spread?.median;
  const comparable = result.strategies.map((strategy) => {
    const raw = deficitFor(strategy);
    return { strategy, deficit: raw == null || raw === "" ? Number.NaN : Number(raw) };
  }).filter((item) => Number.isFinite(item.deficit)).sort((a, b) => a.deficit - b.deficit);
  const cropLabel = (strategy) => strategy.crop === "maize_grain" ? "Corn" : strategy.name.replace(/\s*\(.*\)$/, "");
  const lowestGap = comparable[0];
  const highestGap = comparable.at(-1);
  const requestedSeasons = Math.max(0, Number(result.period.requested[1]) - Number(result.period.requested[0]) + 1);
  const coverageCounts = result.strategies.map((strategy) => ({ name: cropLabel(strategy), count: Number(strategy.result?.seasons_simulated || 0) }));
  const sameFullCoverage = coverageCounts.length > 0 && coverageCounts.every((item) => item.count === requestedSeasons);
  const coverageSummary = sameFullCoverage
    ? `All ${requestedSeasons} requested past seasons were simulated for each option.`
    : `We requested ${requestedSeasons} seasons; valid results: ${coverageCounts.map((item) => `${item.name} ${item.count}`).join(" · ")}. Missing seasons can affect comparisons.`;
  const irrigationNextStep = field.irrigation === "rain-fed"
    ? "For a rain-fed field, compare this with what you know about local rainfall, planting dates, and soil moisture."
    : field.irrigation === "irrigated"
      ? "For an irrigated field, compare the results with reliable water availability, pumping capacity, cost, and local water rules."
      : "Confirm whether this field is rain-fed or irrigated, and how reliable its water source is. That context can change how you read the comparison.";
  const soilNextStep = result.soil
    ? "Check whether the mapped soil description matches what you see in the field; map units can vary within a field."
    : "No mapped soil record was available here. Treat soil-related comparisons cautiously and check local soil information.";
  const foundSummary = lowestGap && highestGap && lowestGap !== highestGap
    ? `Among these options, ${cropLabel(lowestGap.strategy)} had the smallest median modeled rain-fed gap (${farmerWaterDepth(lowestGap.deficit)} per season). ${cropLabel(highestGap.strategy)} had the largest (${farmerWaterDepth(highestGap.deficit)}). This compares past model results for this location.`
    : lowestGap
      ? `We could calculate a median modeled rain-fed gap for ${cropLabel(lowestGap.strategy)} (${farmerWaterDepth(lowestGap.deficit)} per season), but not enough options have valid results for a comparison.`
    : "We do not have enough valid water-gap results to compare the options. Check the data coverage and try another location if needed.";
  const current = result.strategies.find((s) => s.role === "current_practice");
  const ordered = current ? [current, ...result.strategies.filter((s) => s !== current)] : result.strategies;
  const context = { field, metricKey, lowest: comparable.length > 1 ? lowestGap?.strategy : null, alternatives: ordered.filter((s) => s.role !== "current_practice") };
  const reportedDetails=field.details||result.field_context||{};
  const detailLabels={area_acres:"Field size (acres)",soil_texture:"Soil texture you described",soil_test:"Soil test",drainage:"Drainage",slope:"Slope",water_source:"Water source",notes:"Your notes"};
  const detailRows=Object.entries(detailLabels).filter(([key])=>reportedDetails[key]&&reportedDetails[key]!=="unknown").map(([key,label])=>`<li><strong>${label}:</strong> ${esc(reportedDetails[key])}</li>`).join("");
  const priorityList=(reportedDetails.priorities||[]).map(p=>PRIORITIES[p]||p);
  const limits=["budget","equipment","marketing"].filter(k=>reportedDetails[k]&&reportedDetails[k]!=="unknown").map(k=>`${({budget:"Budget",equipment:"Equipment",marketing:"Places to sell"})[k]}: ${LEVEL_TEXT[reportedDetails[k]]||reportedDetails[k]}`);
  const mapInsight = document.createElement("aside");
  mapInsight.className = "analysis-map-insight";
  mapInsight.innerHTML = `<p class="eyebrow">FIELD SNAPSHOT</p><h2>${esc(field.name)}</h2><p>${esc(result.location.state_name)} · NASA weather + mapped USDA soil</p><div class="map-selected-layer"><span>MAP LAYER</span><strong id="map-selected-layer-label">Loading the matching map…</strong></div><p class="small">Relative water-gap score · compared across these options</p><div class="map-risk-list">${result.strategies.map((s,i)=>`<span><i style="background:${["#23533e","#b4532a","#3b5fa8"][i%3]}"></i>${esc(cropLabel(s))} <strong>${s.water_stress_exposure?.percentage == null ? "—" : `${s.water_stress_exposure.percentage}%`}</strong></span>`).join("")}</div><p class="map-disclaimer">Map colors show modeled values in the selected layer. These percentages compare crop options; they are not mapped field measurements. The pin is a location point, not a surveyed field boundary.</p>`;
  document.getElementById("map-pane").querySelector(".analysis-map-insight")?.remove();
  document.getElementById("map-pane").append(mapInsight);
  mapSelection.then(selection=>{
    const label=mapInsight.querySelector('#map-selected-layer-label');
    if(!label)return;
    if(!selection){label.textContent='No matching map scenario is available; comparison remains below.';return;}
    const strategy=result.strategies.find(s=>s.crop===selection.crop)||result.strategies[0];
    label.textContent=`${cropLabel(strategy)} · ${selection.metricLabel} · ${selection.year}`;
  });
  const weather = result.provenance?.weather || {};
  panel.innerHTML = `
    <div class="form-topline"><button type="button" class="back-link" id="result-home">${icon("back")} ${user ? "My land" : "Home"}</button><button type="button" class="secondary-button" id="change-details">${icon("note")} Edit field and priorities</button></div>
    <section class="results-hero"><p class="eyebrow">Plans for ${esc(field.name)}</p><h1>Compare your plans, and see what needs checking</h1>
      <p class="lead">The same ${esc(requestedSeasons)} past seasons near ${esc(result.location.state_name)}, replayed for each crop with the mapped soil. No plan is marked as the right one: a historical comparison can’t weigh prices, yield or local advice.</p></section>
    ${result.mode === "sample" ? `<div class="notice-card" role="note"><strong>Saved example.</strong> Real NASA and USDA records for Hays, Kansas, stored with the app so it works without a live call. It is not your field.</div>` : ""}
    <section class="plan-summary-bar">
      <div><h2>${icon("sprout")} ${esc(field.name)}</h2><p>${esc(result.location.state_name)} · ${Number(field.lat).toFixed(2)}°, ${Number(field.lon).toFixed(2)}°${reportedDetails.area_acres ? ` · ${esc(reportedDetails.area_acres)} acres` : ""}</p><p>Now growing: ${esc(cropName(field.crop))} · ${field.irrigation === "rain-fed" ? "rain-fed" : field.irrigation === "irrigated" ? "irrigated" : "water source not confirmed"}</p><span class="done-chip">${icon("drop")} Priority: ${esc(GOALS[result.goal] || result.goal)}</span></div>
      <div class="warn-card" style="margin:0">${icon("alert")}<div><strong>This comparison is incomplete by design</strong>It covers water and soil from public records. Equipment, market, pest and price questions need your knowledge and an agronomist’s.${limits.length ? ` You noted: ${esc(limits.join(" · "))}.` : ""}</div></div>
    </section>
    ${priorityList.length || detailRows ? `<section class="card"><h2 class="card-title">${icon("info")} Your priorities and field details</h2>${priorityList.length ? `<p>${priorityList.map((p) => `<span class="tag">${esc(p)}</span>`).join(" ")}</p>` : ""}${detailRows ? `<details><summary>Field details you provided</summary><ul>${detailRows}</ul></details>` : ""}<p class="hint">These help you and an expert read the plans. The water calculation uses the mapped USDA soil and the inputs listed under technical details.</p></section>` : ""}
    <div class="section-heading" style="margin-top:26px"><div><p class="eyebrow">Plans side by side</p><h2>Each card answers the same questions</h2></div><span class="hint">Medians across past seasons</span></div>
    <div class="plan-grid">${ordered.map((strategy, index) => planCard(strategy, index, context)).join("")}</div>
    ${soilLayersSection(result)}
    ${seasonChart(result)}
    <section class="decision-guide" aria-labelledby="decision-guide-title"><div class="section-heading"><div><p class="eyebrow">FROM DATA TO A NEXT STEP</p><h2 id="decision-guide-title">What this means for your field</h2></div></div><div class="decision-guide-grid">
      <article class="decision-guide-card"><span class="decision-step">01 · WHAT WE FOUND</span><h3>A past-season comparison</h3><p>${esc(foundSummary)}</p></article>
      <article class="decision-guide-card"><span class="decision-step">02 · WHAT IT MAY MEAN</span><h3>A water signal to consider</h3><p>This estimates how crop water demand compared with past rainfall and mapped soil storage. It is not a measured amount of water missing from your field, and it doesn’t tell you which crop will earn more, yield more, or do best next season.</p></article>
      <article class="decision-guide-card"><span class="decision-step">03 · WHAT TO CHECK NEXT</span><h3>Bring local knowledge in</h3><ul><li>${esc(irrigationNextStep)}</li><li>${esc(soilNextStep)}</li><li>Ask the assistant to explain a number, or send your question and field context to an agronomist.</li></ul></article>
    </div><p class="decision-coverage" role="note"><strong>Data coverage:</strong> ${esc(coverageSummary)} Your field marker is a location point, not a surveyed field boundary.</p></section>
    <div class="two-col">
      <section class="card"><h2 class="card-title">${icon("source")} Data and sources</h2><ul class="sources-list">
        <li><strong>Weather · NASA POWER</strong>${esc(weather.product || "Daily agroclimatology")}${weather.period ? ` · ${esc(weather.period.join(" to "))}` : ""}</li>
        <li><strong>Soil · USDA SSURGO</strong>${esc(result.soil?.label || "No mapped soil record at this point")}</li>
        <li><strong>Soil moisture · NASA SMAP</strong>Recent surface and root-zone estimates, shown for context in Soil layers. Not used in the calculation.</li>
        <li><strong>Equations · FAO-56</strong>Penman–Monteith ET₀, crop coefficients and a daily root-zone water balance. <a href="/science/">See the method</a></li>
        <li><strong>Past seasons</strong>${esc(result.period.requested[0])}–${esc(result.period.requested[1])} · ${esc(coverageSummary)}</li>
      </ul></section>
      <section class="tint-card"><h2 class="card-title">${icon("chat")} Take your questions to an expert</h2><p>Check soil, water, equipment and markets before you change crops. The assistant can explain any number here; an agronomist can give a person’s view.</p>
        <div class="button-row"><button type="button" class="primary" id="open-chat">${icon("chat")} Explain my results</button>${user?`<button type="button" class="secondary-button" id="ask-expert">Ask an agronomist</button>`:`<a class="secondary-button" href="/workspace/?signin=1">Sign in to ask an agronomist</a>`}</div></section>
    </div>
    <div class="actions result-actions"><button type="button" class="quiet-button" id="new-comparison">${icon("refresh")} Compare again</button>${user ? `<button type="button" class="quiet-button" id="all-plans">${icon("layers")} All saved plans</button>` : ""}<button type="button" class="quiet-button" id="show-details">Show technical details</button></div>
    <details class="technical-details" id="technical"><summary>Technical details</summary><div><p>Status: ${esc(result.status)} · mode: ${esc(result.mode)} · analysis: ${esc(result.analysis_id)}</p><p>Location: ${result.location.public_location.lat}, ${result.location.public_location.lon}</p><p class="muted small">${esc(result.summary)}</p><ul>${result.limitations.map((item) => `<li>${esc(item)}</li>`).join("")}</ul><p>Weather source: ${esc(weather.provider)} ${esc(weather.product)}, ${esc((weather.period || []).join(" to "))}.</p></div></details>`;
  wireSoilLayers(panel, result);
  document.getElementById("result-home").onclick = () => user ? showLands() : renderAuth();
  document.getElementById("open-chat").onclick = async () => {
    await openChat(result);
    const input = document.getElementById("chat-input");
    if (input && !input.value) {
      input.value = "In simple terms, what did this comparison find, what should I check next for my field, and what does the data not tell me?";
      input.focus();
    }
  };
  document.getElementById("ask-expert")?.addEventListener("click", () => renderExpertRequest(result, field));
  document.getElementById("all-plans")?.addEventListener("click", () => savedAnalyses());
  document.getElementById("change-details").onclick = () => renderFieldEditor(field, "", 4);
  document.getElementById("new-comparison").onclick = () => startAnalysis(field, result.goal, result.mode);
  document.getElementById("show-details").onclick = () => { document.getElementById("technical").open = true; document.getElementById("technical").scrollIntoView({ behavior: "smooth" }); };
  document.querySelector('.result-actions').insertAdjacentHTML('beforeend',`<a class="quiet-button" href="${API}/analyses/${encodeURIComponent(result.analysis_id)}/report/print" target="_blank" rel="noopener">Export full report · PDF</a><a class="quiet-button" href="${API}/analyses/${encodeURIComponent(result.analysis_id)}/report" target="_blank" rel="noopener">Markdown report</a>`);
  document.getElementById('technical').insertAdjacentHTML('beforeend', `<div>${result.strategies.map(s=>`<h3>${esc(s.name)} assumptions</h3><p>Planting: ${esc(s.planting)} · Initial Kc: ${esc(s.parameters.kc_ini)} · Root depth: ${esc(s.result?.root_depth_m ?? 'unavailable')} m</p><ul>${Object.entries(s.parameters.sources).map(([k,v])=>`<li>${esc(k)}: ${esc(v)}</li>`).join('')}</ul>`).join('')}</div>`);
}

function renderExpertRequest(analysis, field, observation=null) {
  if (!user) { renderAuth("register", "Create an account or sign in to send a private request to an agronomist."); return; }
  setMapVisible(false);
  const contextLine=analysis?`${field.name} · ${analysis.location.state_name} · ${analysis.period.requested.join('–')} · comparison attached`:`${field.name} · ${field.state||'Saved field'} · private note from ${observation?.observed_on||''}`;
  const starter=observation?`Could you help me understand this field observation?\n\n${observation.note}`:'';
  panel.innerHTML = `<div class="form-topline"><button type="button" class="back-link" id="expert-back">← ${observation?'Field journal':'Crop comparison'}</button><span class="step-label">AGRONOMIST SUPPORT</span></div>
    <section class="expert-request-card"><p class="eyebrow">ASK A HUMAN EXPERT</p><h1>What would you like help with?</h1><p class="lead">${observation?'Your note and field profile will be shared with the agronomist for this request.':'Your field profile and this comparison will be shared with the agronomist for this request.'} Replies appear in your account.</p><div class="notice-card"><strong>${esc(contextLine)}</strong></div>
    <form id="expert-request-form"><label for="expert-message">Your question</label><textarea id="expert-message" rows="5" minlength="10" maxlength="3000" required placeholder="For example: Which option should I discuss with my local seed advisor, given the drainage on this field?">${esc(starter)}</textarea><p class="hint">Only send details you want the agronomist to see. The reply is guidance for discussion, not a confirmed diagnosis.</p><div class="form-actions"><button class="primary" type="submit">Send request</button><button class="quiet-button" type="button" id="expert-cancel">Cancel</button></div></form></section>`;
  const returnToContext=()=>analysis?renderAnalysis(analysis,field):renderFieldObservations(field);
  document.getElementById("expert-back").onclick = returnToContext;
  document.getElementById("expert-cancel").onclick = returnToContext;
  document.getElementById("expert-request-form").onsubmit = async (event) => {
    event.preventDefault();
    const submit = event.currentTarget.querySelector("button[type=submit]");
    submit.disabled = true; submit.textContent = "Sending…";
    try {
      await getJSON(`${API}/expert/requests`, { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: document.getElementById("expert-message").value.trim(), field_id: field.id || null, analysis_id: analysis?.analysis_id || null, observation_id:observation?.id||null }) });
      await myExpertRequests("Your request was sent to the agronomist queue.");
    } catch (err) {
      const error = document.createElement("div"); error.className = "errors"; error.setAttribute("role", "alert"); error.textContent = err.message;
      event.currentTarget.prepend(error); submit.disabled = false; submit.textContent = "Send request";
    }
  };
}

async function myExpertRequests(message = "") {
  if (!user) return renderAuth();
  setMapVisible(false);
  panel.innerHTML = `<section class="loading-card"><span class="loader"></span><p>Loading your expert requests…</p></section>`;
  try {
    const result = await getJSON(`${API}/expert/requests`);
    panel.innerHTML = `<div class="form-topline"><button type="button" class="back-link" id="expert-home">← My fields</button><span class="step-label">AGRONOMIST SUPPORT</span></div><p class="eyebrow">YOUR INBOX</p><h1>Expert questions and replies</h1><p class="lead">Private requests linked to your fields and crop comparisons.</p>${message?`<div class="notice-card" role="status">${esc(message)}</div>`:""}${result.requests.length?`<div class="expert-request-list">${result.requests.map((item)=>`<article class="expert-thread"><div class="expert-thread-head"><strong>${esc(item.field_name||"Field question")}</strong><span class="state-pill ${item.status}">${item.status==="replied"?"Reply received":"Waiting for reply"}</span></div><p>${esc(item.message)}</p><span class="hint">Sent ${esc(new Date(item.created_utc).toLocaleString())}</span>${item.response?`<div class="expert-reply"><strong>Agronomist reply</strong><p>${esc(item.response)}</p><span class="hint">${esc(item.responded_utc?new Date(item.responded_utc).toLocaleString():"")}</span></div>`:""}</article>`).join("")}</div>`:`<section class="empty-state"><h2>No expert requests yet</h2><p>Open a crop comparison and choose “Ask an agronomist” to send a question with your field context.</p></section>`}`;
    document.getElementById("expert-home").onclick = () => showHome();
  } catch (err) {
    panel.innerHTML = `<h1>Your inbox isn’t available</h1><div class="errors">${esc(err.message)}</div><button id="expert-home" class="primary">Back to my fields</button>`;
    document.getElementById("expert-home").onclick = () => showHome();
  }
}

async function openChat(analysis) {
  const ownerVersion=authVersion;
  setMapVisible(false);
  panel.innerHTML = `<section class="loading-card"><span class="loader"></span><p>Opening your crop conversation…</p></section>`;
  try {
    const existing = await getJSON(`${API}/chat/sessions`);
    if(ownerVersion!==authVersion)return;
    const previous = existing.sessions.find(s=>s.analysis_id===analysis.analysis_id);
    if (previous) { chatSession=previous.session_id; const saved=await getJSON(`${API}/chat/sessions/${encodeURIComponent(chatSession)}`); if(ownerVersion!==authVersion)return; return renderChat(analysis,saved.messages); }
    const session = await getJSON(`${API}/chat/sessions`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ analysis_id: analysis.analysis_id }) });
    if(ownerVersion!==authVersion)return;
    chatSession = session.session_id;
    renderChat(analysis, []);
  } catch (err) {
    if(ownerVersion!==authVersion)return;
    panel.innerHTML = `<h1>Chat isn’t available right now</h1><div class="errors">${esc(err.message)}</div><button class="primary" id="back-results">Back to comparison</button>`;
    document.getElementById("back-results").onclick = () => renderAnalysis(analysis, fields.find((item) => item.id === analysis.field_id) || activeField || fields[0]);
  }
}

function renderChat(analysis, messages, error = "") {
  panel.innerHTML = `
    <div class="form-topline"><button type="button" class="back-link" id="back-results">← Crop comparison</button><span class="step-label">FIELD SHIFT CHAT</span></div>
    <section class="chat-header"><div class="chat-avatar">✳</div><div><p class="eyebrow">YOUR FIELD CONVERSATION</p><h1>Let’s explore your options</h1><p class="muted">Ask about the comparison, or tell me which crop you’d like to consider.</p></div></section>
    <div class="chat-boundary"><strong>What this chat can do:</strong> explain the comparison and point to the evidence. It can’t guarantee the best crop, diagnose a problem, or replace local farm advice.</div>
    <div id="chat-messages" class="chat-messages">${messages.map((item) => chatMessage(item.question, item.response)).join("") || `<div class="assistant-message"><strong>Field Shift</strong><p>I can help explain the past-season comparison for this field. What would you like to know?</p></div>`}</div>
    ${error ? `<div class="errors" role="alert">${esc(error)}</div>` : ""}
    <div class="prompt-chips"><button type="button" data-prompt="Which crop had the lower past irrigation need?">Compare water needs</button><button type="button" data-prompt="What does this comparison tell me about my field?">Explain my field</button><button type="button" data-prompt="I want to consider a different crop. What should I compare?">Consider another crop</button></div>
    <form id="chat-form" class="chat-form"><label class="sr-only" for="chat-input">Your question</label><textarea id="chat-input" name="message" rows="2" maxlength="4000" placeholder="Ask a question about your field…" required></textarea><button class="primary" type="submit">Send</button></form>
    <p class="hint">Answers use the saved comparison and cited information. Crop parameters in this release are still under review.</p>`;
  document.getElementById("back-results").onclick = () => renderAnalysis(analysis, fields.find((field) => field.id === analysis.field_id) || activeField || fields[0]);
  document.querySelector('.form-topline').insertAdjacentHTML('beforeend','<button class="quiet-button" id="manage-chat">Conversations</button>');
  document.getElementById('manage-chat').onclick = () => manageConversations(analysis);
  panel.querySelectorAll("[data-prompt]").forEach((button) => button.onclick = () => {
    document.getElementById("chat-input").value = button.dataset.prompt;
    document.getElementById("chat-input").focus();
  });
  document.getElementById("chat-form").onsubmit = async (event) => {
    event.preventDefault();
    const input = document.getElementById("chat-input");
    const question = input.value.trim();
    if (!question || busy) return;
    busy = true;
    const ownerVersion=authVersion;
    const history = [...messages, { question, response: null }];
    renderChat(analysis, history);
    try {
      const response = await getJSON(`${API}/chat/sessions/${encodeURIComponent(chatSession)}/messages`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message: question, language: "auto" }),
      });
      if(ownerVersion!==authVersion)return;
      busy = false;
      renderChat(analysis, [...messages, { question, response }]);
    } catch (err) {
      if(ownerVersion!==authVersion)return;
      busy = false;
      renderChat(analysis, messages, err.message);
    }
  };
  const messageBox = document.getElementById("chat-messages");
  messageBox.scrollTop = messageBox.scrollHeight;
}

// Say why AI selection is off, from the backend's service_status, instead of a vague "unavailable".
function chatServiceNote(response) {
  if (response.mode === 'openai_evidence_selection') return 'AI-assisted evidence selection';
  return ({
    quota_exhausted: 'AI answers are paused: the OpenAI account for this app has no credits left. This answer comes straight from your saved comparison.',
    access_denied: 'AI answers are off: the OpenAI key was rejected. This answer comes straight from your saved comparison.',
    not_configured: 'AI answers aren’t set up on this server. This answer comes straight from your saved comparison.',
  })[response.service_status] || response.service_notice || 'AI service unavailable · this answer comes straight from your saved comparison.';
}

function chatMessage(question, response) {
  if (!response) return `<div class="user-message"><p>${esc(question)}</p></div><div class="assistant-message"><span class="loader"></span><p>Finding relevant information…</p></div>`;
  return `<div class="user-message"><p>${esc(question)}</p></div><div class="assistant-message" dir="auto"><strong>Field Shift</strong><p class="hint">${esc(chatServiceNote(response))}</p>${chatAnswer(response)}
    ${response.evidence?.length ? `<div class="evidence-list"><span class="hint">Sources and evidence</span>${response.evidence.map((item) => `<details><summary>${esc(item.title)}</summary><p>${esc(item.text)}</p><a href="${esc(item.url)}" target="_blank" rel="noopener">Open source</a></details>`).join("")}</div>` : ""}
    ${response.questions?.length ? `<div class="follow-up"><span class="hint">To make this more useful:</span>${response.questions.map((q) => `<p>${esc(q)}</p>`).join("")}</div>` : ""}
    <p class="hint">${esc(response.limitation || "")}</p></div>`;
}

// ---------- start ----------
function chatAnswer(response){
  const cards=(response.evidence||[]).filter(card=>card.id!=='analysis-limits');
  if(!cards.length)return `<p>${esc(response.answer).replaceAll('\n','<br>')}</p>`;
  const names={irrigated_net_irrigation:'Net irrigation need',rainfed_deficit:'Rain-fed water deficit',etc_standard:'Crop water demand',et0:'Reference ET₀',precipitation:'Rainfall'};
  return `<p>${response.language==='ar'?'الأدلة المتاحة من المقارنة والمصادر:':'Evidence from this comparison and its sources:'}</p>`+cards.map(card=>`<p><strong>${esc(card.title.replace('Maize (grain, field corn)','Corn').replace(/:\s*([a-z_]+)$/,(_,key)=>': '+(names[key]||key)))}</strong><br>${esc(card.text)}</p>`).join('')+`<p class="hint">${response.language==='ar'?'لم يتم التحقق من دقة تقديرات الري على مستوى الحقل.':'Field irrigation accuracy is not validated. See the saved analysis limitations below.'}</p>`;
}

(async function start() {
  setHeader();
  try { catalog = await getJSON(`${API}/crops`); } catch { /* account flow can still load */ }
  try {
    const result = await getJSON(`${API}/auth/me`);
    user = result.user;
  } catch { user = null; }
  setHeader();
  if (new URLSearchParams(location.search).get('demo')==='ks_hays') await runDemo();
  else if (user) await showHome();
  else renderAuth('login');
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
})();

function runDemo(){ return startAnalysis({name:'Hays, Kansas · saved example',lat:38.85,lon:-99.33,crop:'maize_grain',irrigation:'unknown',history:[]},'conserve_water','sample'); }

function seasonChart(result) {
  const strategies=result.strategies.filter(s=>s.result?.seasons?.length);
  if(!strategies.length)return '';
  const metric=result.goal==='reduce_drought_stress'?'rainfed_deficit':'irrigated_net_irrigation';
  const years=[...new Set(strategies.flatMap(s=>s.result.seasons.map(y=>y.year)))].sort();
  const high=Math.max(1,...strategies.flatMap(s=>s.result.seasons.map(y=>y[metric]||0)))*1.08;
  const colors=['#2f6b3b','#a96637','#546d99'];
  return `<section class="season-chart"><h2>How past seasons varied</h2><p class="hint">${metric==='rainfed_deficit'?'Rain-fed water deficit':'Net irrigation need'} · mm per season · gaps mean excluded seasons</p><svg viewBox="0 0 820 250" role="img" aria-label="Historical seasonal water comparison, ${years[0]} to ${years.at(-1)}"><title>Historical water requirements in millimeters; no future prediction</title>${[0,.5,1].map(t=>`<path d="M48 ${210-t*180}H800" stroke="#dce2d5"/><text x="5" y="${214-t*180}" font-size="12" fill="#526257">${Math.round(high*t)}</text>`).join('')}${strategies.map((s,i)=>s.result.seasons.map(y=>`<circle cx="${48+(y.year-years[0])*750/Math.max(1,years.at(-1)-years[0])}" cy="${210-y[metric]/high*180}" r="3" fill="${colors[i]}"><title>${esc(s.name)}, ${y.year}: ${y[metric]} mm</title></circle>`).join('')).join('')}<text x="48" y="240" font-size="12">${years[0]}</text><text x="760" y="240" font-size="12">${years.at(-1)}</text></svg><div class="chart-labels">${strategies.map((s,i)=>`<span style="color:${colors[i]}">● ${esc(s.name)}</span>`).join('')}</div></section>`;
}

function recoverAccount(error='') {
  if(typeof error!=='string')error='';
  busy=false;setMapVisible(false);
  panel.innerHTML=`<section class="auth-wrap"><p class="eyebrow">ACCOUNT RECOVERY</p><h1>Use your recovery code</h1><p class="lead">Enter the code you saved when you created your account. No recovery email is sent.</p>${error?`<p class="errors" role="alert">${esc(error)}</p>`:''}<form id="recover-form" class="auth-form"><label for="recover-email">Email</label><input id="recover-email" name="email" type="email" required autocomplete="email"><label for="recover-code">Recovery code</label><input id="recover-code" name="code" required autocomplete="off" minlength="20"><label for="recover-password">New password</label><input id="recover-password" name="password" type="password" required minlength="12" maxlength="128" autocomplete="new-password"><button class="primary" type="submit">Reset password</button></form><button id="recover-back" class="link">Back to sign in</button></section>`;
  document.getElementById('recover-back').onclick=()=>renderAuth();
  document.getElementById('recover-form').onsubmit=async e=>{e.preventDefault();const d=new FormData(e.currentTarget);const b=e.currentTarget.querySelector('button');b.disabled=true;try{const r=await getJSON(`${API}/auth/recover`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:d.get('email'),password:d.get('password'),recovery_code:d.get('code')})});authVersion++;user=null;fields=[];currentAnalysis=null;setHeader();showRecoveryCode(r.recovery_code);document.getElementById('continue-home').onclick=()=>renderAuth();}catch(err){recoverAccount(err.message);}};
}

function renderPlans() {
  if (currentAnalysis) return renderAnalysis(currentAnalysis, activeField);
  if (user) return savedAnalyses();
  setMapVisible(false);
  setTab("plans");
  panel.innerHTML = stateCard("layers", "No plans yet", "Add your field and compare crops on it, or open the saved Kansas example to see what a plan looks like.",
    `<button type="button" class="primary" id="plans-add">${icon("plus")} Add your field</button><button type="button" class="secondary-button" id="plans-demo">See a saved example</button>`);
  document.getElementById("plans-add").onclick = () => renderFieldEditor();
  document.getElementById("plans-demo").onclick = runDemo;
}

async function savedAnalyses() {
  const ownerVersion=authVersion;
  setMapVisible(false);busy=false;setTab("plans");
  panel.innerHTML = skeleton();
  try { const r=await getJSON(`${API}/account/analyses`);
    if(ownerVersion!==authVersion)return;
    panel.innerHTML=`<section class="journal-header"><div><p class="eyebrow">Your plans</p><h1>Saved comparisons</h1><p class="lead">Each comparison keeps the source records and assumptions used at the time.</p></div><button type="button" class="primary" id="plans-new">${icon("plus")} Compare a field</button></section>${r.analyses.length?`<div class="field-grid">${r.analyses.map(a=>`<article class="field-card"><div class="field-card-top"><span class="field-glyph">${icon("layers")}</span><span class="state-pill">${esc(a.mode==='sample'?'Saved example':a.state)}</span></div><h3>${esc(fields.find(f=>f.id===a.field_id)?.name||a.state)}</h3><p class="muted">${esc(GOALS[a.goal]||a.goal)}</p><p class="field-coords">${esc(a.period.join('–'))} · ${esc(new Date(a.created_utc).toLocaleDateString())}</p><div class="field-card-actions"><button type="button" class="secondary-button" data-analysis="${esc(a.id)}">Open plan</button></div></article>`).join('')}</div>`:stateCard("layers","No saved plans yet","Choose one of your fields and compare crop plans for it. Each comparison is saved here with its sources.",`<button type="button" class="secondary-button" id="plans-demo">See a saved example</button>`)}`;
    document.getElementById("plans-new").onclick=()=>showLands();
    document.getElementById("plans-demo")?.addEventListener("click",runDemo);
    panel.querySelectorAll('[data-analysis]').forEach(b=>b.onclick=async()=>{b.disabled=true;try{const saved=await getJSON(`${API}/analyses/${encodeURIComponent(b.dataset.analysis)}`);if(ownerVersion!==authVersion)return;currentAnalysis=saved;activeField=fields.find(f=>f.id===currentAnalysis.field_id)||null;renderAnalysis(currentAnalysis,activeField);}catch(e){b.disabled=false;b.textContent=e.message;}});
  } catch(e){
    if(ownerVersion!==authVersion)return;
    panel.innerHTML=stateCard("alert","We couldn’t load your plans",e.message,`<button type="button" class="primary" id="plans-retry">${icon("refresh")} Try again</button>`,"error");
    document.getElementById("plans-retry").onclick=()=>savedAnalyses();
  }
}

async function renderNotesHub() {
  setMapVisible(false);
  setTab("notes");
  if (!user) {
    panel.innerHTML = stateCard("note", "Sign in to keep field notes", "Field notes are private, dated records of what you notice — with photos if you like. They need an account so they stay yours.",
      `<button type="button" class="primary" id="notes-signin">Sign in</button><button type="button" class="secondary-button" id="notes-register">Create an account</button>`);
    document.getElementById("notes-signin").onclick = () => renderAuth("login");
    document.getElementById("notes-register").onclick = () => renderAuth("register");
    return;
  }
  const ownerVersion = authVersion;
  panel.innerHTML = skeleton();
  try {
    fields = (await getJSON(`${API}/fields`)).fields;
    if (ownerVersion !== authVersion) return;
  } catch (err) {
    if (ownerVersion !== authVersion) return;
    panel.innerHTML = stateCard("alert", "We couldn’t load your fields", err.message, `<button type="button" class="primary" id="notes-retry">${icon("refresh")} Try again</button>`, "error");
    document.getElementById("notes-retry").onclick = () => renderNotesHub();
    return;
  }
  panel.innerHTML = `<section class="journal-header"><div><p class="eyebrow">Field notes</p><h1>What have you noticed?</h1><p class="lead">Private notes for each field: water, crop growth, weather damage, pests or disease. Nothing is published; an agronomist only sees a note you choose to send.</p></div></section>
    ${fields.length ? `<div class="field-grid">${fields.map((field) => `<article class="field-card"><div class="field-card-top"><span class="field-glyph">${icon("note")}</span><span class="state-pill">${esc(field.state)}</span></div><h3>${esc(field.name)}</h3><p class="muted">Current crop · ${esc(cropName(field.crop))}</p><div class="field-card-actions"><button type="button" class="secondary-button" data-open-notes="${esc(field.id)}">Open notes</button><button type="button" class="quiet-button" data-new-note="${esc(field.id)}">${icon("plus")} Add a note</button></div></article>`).join("")}</div>`
      : stateCard("sprout", "Add a field first", "Notes belong to a field. Add one, then come back to record what you notice.", `<button type="button" class="primary" id="notes-add">${icon("plus")} Add a field</button>`)}`;
  document.getElementById("notes-add")?.addEventListener("click", () => renderFieldEditor());
  panel.querySelectorAll("[data-open-notes]").forEach((b) => b.onclick = () => renderFieldObservations(fields.find((f) => f.id === b.dataset.openNotes)));
  panel.querySelectorAll("[data-new-note]").forEach((b) => b.onclick = () => renderObservationForm(fields.find((f) => f.id === b.dataset.newNote)));
}

function deleteField(field) {
  panel.innerHTML=`<section class="auth-wrap"><h1>Remove ${esc(field.name)}?</h1><p>The field will be removed from your account. Existing analysis snapshots remain in Saved comparisons.</p><button class="primary" id="confirm-remove">Remove field</button><button class="quiet-button" id="cancel-remove">Keep field</button><p id="remove-error" class="errors" hidden></p></section>`;
  document.getElementById('cancel-remove').onclick=()=>showHome();
  document.getElementById('confirm-remove').onclick=async e=>{e.currentTarget.disabled=true;try{await getJSON(`${API}/fields/${encodeURIComponent(field.id)}`,{method:'DELETE'});await showHome('Field removed.');}catch(err){document.getElementById('remove-error').hidden=false;document.getElementById('remove-error').textContent=err.message;}};
}

function accountSettings(error='') {
  if(typeof error!=='string')error='';
  setMapVisible(false);busy=false;
  panel.innerHTML=`<section class="auth-wrap"><p class="eyebrow">YOUR ACCOUNT</p><h1>${esc(user?.name||'Account')}</h1><p>${esc(user?.email)}</p>${error?`<p class="errors">${esc(error)}</p>`:''}<h2>Your data stays yours.</h2><p>Download your fields, saved comparisons and conversation history as JSON. Passwords and recovery codes are never included.</p><button class="secondary-button" id="export-account">Download my data</button><hr><details><summary>Delete account</summary><p>This permanently deletes your account, private fields, analyses and conversations. Shared public-source caches are retained. Download your data first.</p><form id="delete-account"><label for="delete-password">Confirm your password</label><input type="password" id="delete-password" name="password" required minlength="12" autocomplete="current-password"><label class="choice-card"><input type="checkbox" required>I understand this cannot be undone.</label><button class="primary" type="submit">Permanently delete my account</button></form></details><a href="/science/">Methods and limitations</a></section>`;
  document.getElementById('export-account').onclick=async e=>{const button=e.currentTarget;button.disabled=true;try{const data=await getJSON(`${API}/account/export`);const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='field-shift-account.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);button.disabled=false;}catch(err){accountSettings(err.message);}};
  document.getElementById('delete-account').onsubmit=async e=>{e.preventDefault();const data=new FormData(e.currentTarget);e.currentTarget.querySelector('button').disabled=true;try{await getJSON(`${API}/auth/account`,{method:'DELETE',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:data.get('password')})});authVersion++;user=null;fields=[];activeField=null;currentAnalysis=null;chatSession=null;setHeader();renderAuth();}catch(err){accountSettings(err.message);}};
}

async function manageConversations(analysis) {
  try {
    const r=await getJSON(`${API}/chat/sessions`);
    panel.innerHTML=`<h1>Your conversations</h1><p>Up to 10 saved conversations. Remove an older conversation to make room.</p>${r.sessions.map(s=>`<article class="saved-row"><div>${esc(new Date(s.created_utc).toLocaleString())}<p class="hint">${s.analysis_id===analysis.analysis_id?'This comparison':'Another comparison'}</p></div><button class="quiet-button" data-chat-delete="${esc(s.session_id)}">Remove</button></article>`).join('')}<button class="primary" id="chat-return">Back to comparison</button>`;
    document.getElementById('chat-return').onclick=()=>renderAnalysis(analysis,activeField);
    panel.querySelectorAll('[data-chat-delete]').forEach(b=>b.onclick=async()=>{b.disabled=true;try{await getJSON(`${API}/chat/sessions/${encodeURIComponent(b.dataset.chatDelete)}`,{method:'DELETE'});await manageConversations(analysis);}catch(e){b.textContent=e.message;}});
  }catch(e){renderAnalysis(analysis,activeField);}
}
