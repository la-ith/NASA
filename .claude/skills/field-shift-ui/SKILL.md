---
name: field-shift-ui
description: How to build and change the Field Shift web UI (the vanilla-JS PWA in frontend/) without breaking its design system, its honesty rules or its /api/v2 integration. Use this skill whenever a task touches anything under frontend/ — the landing page (index.html, home.js, site.css), the workspace app (workspace/index.html, app.js, styles.css, workspace.css), the methods page (science/, science.js, science.css), the MapLibre map or map-layers.js, result screens, charts, the chat panel, sign-in/accounts screens, the service worker, or frontend tests — and also when wiring a new backend endpoint into the browser, adding a screen, restyling, fixing UI bugs, improving accessibility or dark/print styles, even if the user just says "the page", "the app", "the map", "the dashboard" or "the UI".
---

# Field Shift UI

Field Shift shows farmers how past seasons of NASA POWER weather and USDA SSURGO soil data play through FAO-56 water-balance equations for corn, soybean and sorghum. The UI's job is to **present backend results honestly**. It never does the science itself.

The user designs the final frontend themselves. Treat what is here as their design and change it narrowly: match the existing look, don't redesign screens nobody asked about, and keep diffs small.

## Map of the frontend

FastAPI serves `frontend/` statically at `/`, mounted after the `/api` routes (`backend/app/main.py`). There's no build step, bundler or framework: plain ES modules and CSS.

| Page | HTML | JS | CSS (load order matters) |
|---|---|---|---|
| Landing `/` | `index.html` | `home.js` | `site.css` |
| Workspace `/workspace/` | `workspace/index.html` | `app.js` (+ `map-layers.js`, `soil-profile.js`) | MapLibre CSS → `styles.css` → `site.css` → `workspace.css` → `theme.css` |
| Methods `/science/` | `science/index.html` | `science.js` | `site.css` → `science.css` → `theme.css` |

`theme.css` loads last on every page. It holds the current look: field-paper background, deep green, and liquid-glass chrome (app bar, tab bar, map controls, hero cards). It has fallbacks for no `backdrop-filter`, reduced transparency and high contrast. Put the blur on a `::before` layer, never on an element that contains `position: fixed` children (a backdrop-filter traps them). Reading surfaces stay near-opaque for contrast.

Workspace structure: four tabs (`data-tab` home, land, plans, notes), each screen calling `setTab(name)`; a 4-step add-field wizard (`renderFieldEditor(field, error, step)`, one form whose steps toggle `hidden`); plan cards (`planCard`); and the soil-layers view (`soil-profile.js`). That view draws a to-scale cross-section from the analysis (root depth, TAW/RAW, SSURGO depth) plus the latest NASA SMAP value from `/api/v2/products/smap/query`. Shared helpers: `icon(name)`, `stateCard()`, `skeleton()`, `errorBanner()`. Static assets use `?v=N` cache-busting that must match the `FILES` list in `sw.js`.

Other pieces:
- `sw.js` caches the app shell. API calls always go to the network.
- `v1/` is the historical Hebron regression app. Leave it alone.
- `assets/` holds illustrations; `icon.svg` is the favicon.
- `tests/coverage.test.mjs` runs with `node --test`.

**Service worker rule:** whenever you add, rename or remove a shell file (any HTML, JS, CSS or asset a page loads), update the `FILES` list in `sw.js` and bump the `SHELL` version string (`field-shift-shell-vN`). Otherwise returning users keep stale files.

### How the workspace app is put together (`app.js`)
- `const API = "/api/v2"`. Every request goes through `getJSON(url, options)`, which sends same-origin credentials, parses errors from `{error:{message}}`, `{detail}` or 422 `{error:{fields}}`, and throws an `Error` carrying `.status` and `.body`. Reuse it rather than calling `fetch` directly.
- Screens are functions that set `panel.innerHTML` and then attach handlers by id: `renderHome`, `renderFieldEditor`, `renderAnalysis`, `renderChat`, `renderAuth`, `accountSettings`, and so on. Follow that pattern; don't bring in a framework.
- Module-level state: `user`, `catalog`, `fields`, `activeField`, `currentAnalysis`, `chatSession`, `busy`, `authVersion`, `fieldLocationToken`.
- **Async race guards are load-bearing.** Before rendering an awaited result, check it is still current:
  - Capture `const ownerVersion = authVersion` and return early if it changed. This covers sign-in/out while a job runs.
  - Capture a request token the same way `fieldLocationToken` does in `chooseLocation`.
  
  The tests check this behaviour. Copy the pattern into any new async screen.
- `busy` prevents double submits. Reset it on every exit path, including `catch`.

## Non-negotiable rules

These rules exist because the product's credibility depends on them. A pretty screen that breaks one is a regression.

1. **No science in the browser.** Every number shown (ET₀, ETc, deficits, irrigation, stress days, medians and spreads) comes from the API response. Formatting is fine: rounding, units, choosing the median the backend computed. Recomputing, interpolating, averaging seasons yourself, or reading values off map colours is not. `map-layers.js` states this: source imagery and computed grids stay separate, and no values are inferred from colours.
2. **Historical replay, not forecast.** Results describe how past seasons (for example 2001–2025) would have played out. Label them that way ("historical comparison", "past seasons", "Historical replay"). Never write "will", "predicted", "recommended irrigation", "yield forecast" or accuracy percentages. Keep the existing "not a recommendation or forecast" notices and the "Research preview" framing, and point to `/science/#validation` or `/api/v2/validation/status` instead of making accuracy claims.
3. **Show what's missing.** When a value is absent, show "Not available" or an explicit label, never `0`, `NaN`, `undefined` or a blank. Keep the backend's provenance distinctions visible:
   - farmer-entered, estimated, assumed and missing inputs;
   - coverage states such as supported, partial, unknown, unsupported and not_integrated;
   - `unchecked` never means confirmed coverage;
   - excluded seasons appear as gaps.
4. **`mode` is always explicit.** Analysis requests send `mode: "live"` or `mode: "sample"`. Saved or demo data must be visibly labelled as a saved example (for instance "Hays, Kansas · saved example"). When a live call fails with `sample_available: true`, offer the sample run without passing it off as live.
5. **Escape everything.** Any API or user text placed in `innerHTML` goes through `esc()`, including names, messages, crop ids, error text and chat replies. Use `textContent` or `replaceChildren` where it's easy, as `home.js` does.
6. **No secrets in the browser.** Never put provider keys (OpenAI, CIMIS, Earthdata and others) in frontend code, URLs, `localStorage` or request bodies. The chat goes through `/api/v2/chat/...` on the server. Auth relies on an httpOnly cookie, and the backend rejects cross-origin writes, so keep requests same-origin.
7. **Async jobs, not blocking calls.** `POST /api/v2/analyses` returns 202 with a `status_url`. Poll it about every 900 ms, show friendly stage text from `status.stage`, and stop on `succeeded` (then fetch `analysis_url`) or `failed` (show `status.error.message`).
8. **Map failure must not block analysis.** The map uses MapLibre GL **4.7.1** from unpkg with the OpenFreeMap `positron` style. If tiles or layers fail, show a short status ("Map data unavailable. Field analysis still works.") and let users enter coordinates. Keep the Lower 48, Alaska and Hawaii shortcuts working, including for points across the antimeridian.

Endpoint shapes and fields are in `references/api-contracts.md`. Read it before wiring or changing any API call.

## Visual language

There are two token sets, one per page family. Use variables rather than raw hex so dark mode and print keep working.

- **Marketing and methods pages (`site.css`):**
  - Colours: `--ink #193e31`, `--body #526257`, `--paper #f8f8f1`, `--line #dce2d5`, `--lime #deebbb`, `--light #edf1e6`, `--muted #788275`.
  - Fonts: DM Sans for body text, Manrope for the wordmark and headings.
  - Italic Georgia `<em>` for the second line of a headline ("Know your field.<br><em>Plan what's next.</em>").
  - Components: `.btn` (with `.btn-small`, `.btn-light`, `.btn-outline`), `.quiet-link` ending in `<span>→</span>`, `.eyebrow`, `.soft-pill`, `.section-shell`.
  - Pages are light-themed (`data-theme="light"`).
- **Workspace app (`styles.css`, `workspace.css`):**
  - Base colours: `--bg`, `--surface`, `--text`, `--muted`, `--line`, `--brand #2f6b3b`, `--brand-text`, `--focus`.
  - Label pairs `--{favorable|mixed|concern|insufficient|rejected}-bg` / `--…`, used by `.badge.favorable`, `.badge.mixed`, `.badge.concern`, `.badge.insufficient_evidence` and `.badge.rejected`.
  - Chart colours: `--chart-bar`, `--chart-recent`, `--chart-line`, `--chart-station`.
  - Dark mode is defined in two places: `@media (prefers-color-scheme: dark) :root:not([data-theme="light"])` and `:root[data-theme="dark"]`. When you add a token, add it to `:root` **and** both dark blocks.
  - Print styles exist. Mark controls that shouldn't print with `.no-print`.
- **Layout:** the workspace is `.layout`, with the map pane plus a 520 px panel at ≥980 px and stacked below that. Sections use clamp-based padding. Every page needs to work at phone width without horizontal scrolling.
- **Copy voice:** short, warm and plain, for farmers.
  - Say "Corn", not `maize_grain`; use `plainCropName` and `cropName`.
  - Say "Finding past weather…", not "retrieving_weather".
  - Keep units visible. Water amounts are **inches first, mm alongside** (`inches()` in `app.js`, `inch()` in `soil-profile.js`); US farmers think in inches and acres.
  - Lead with the answer: the plans page opens with `bottomLine()` (crops ranked by the backend median for the farmer's priority). Each plan card shows two numbers; everything else goes behind "More about this plan".
  - Plain words first, technical names second and small, e.g. "water the crop can use (TAW)", never a bare "TAW", "ET₀" or "m³/m³".
  - Text is 17px on the workspace and hints at least ~14px; phones are used outdoors.
  - Use sentence-case headings. Section labels are uppercase eyebrows.
- **Charts** are hand-built inline SVG (see `seasonChart`). They need `role="img"`, an `aria-label` naming the years, a `<title>` that says "no future prediction", per-point `<title>` tooltips, a legend, and visible gaps for excluded seasons.

## Accessibility checklist

Run through this for every UI change:
- Keep the skip link working (`.skip-link` → `#main` or `#panel`, which has `tabindex="-1"`). For new screens, move focus to the panel or its heading after rendering. The app doesn't do this everywhere yet, so don't remove the places where it does (for example the focus on `#chat-input`).
- Use real `<button>` and `<a>` elements. Toggle groups use `aria-pressed` and live inside `role="group"` with an `aria-label`.
- Text that updates asynchronously (stage text, map status, metrics) goes in `aria-live="polite"`.
- Form inputs have `<label>`s. Errors are shown as text, not colour alone, and badges carry words.
- Focus stays visible (`:focus-visible` outline). Contrast holds in light and dark.
- Decorative SVGs get `aria-hidden="true"`; meaningful images get `alt`.

## Workflow

1. Read the files you'll touch, plus the relevant section of `references/api-contracts.md`. Check what the API actually returns (`docs/backend-handoff.md`, `docs/scientific-delivery.md`, or `backend/app/api/*.py`) instead of guessing field names.
2. Make the smallest change that fits the existing patterns. Add no new dependencies or CDNs unless asked; MapLibre 4.7.1 and Google Fonts are the existing externals.
3. Update `sw.js` if shell files changed.
4. Verify:
   - `node --test frontend/tests/` passes. These tests need Node 18+. If `node` isn't on PATH, say so plainly rather than claiming the tests pass.
   - Run the app (the backend serves the frontend; see `.claude/launch.json` or `compose.yaml`), open the changed page in the browser pane, and check the console for errors.
   - Try light, dark (`data-theme`) and a 375 px width.
   - For results screens, use the saved example (`/workspace/?demo=ks_hays`, data from `data/fixtures/showcase_ks_hays.json` via `/api/v2/showcase`) so the check doesn't depend on live NASA calls.
5. Add or extend a test in `frontend/tests/` when you change logic: race guards, metric formatting, chart output, or "Not available" handling. The existing tests extract functions from `app.js` by name with `source.indexOf('function name(')` and run them in `vm`. **Renaming or reordering `startAnalysis`, `metricValue`, `renderAnalysis`, `seasonChart`, `recoverAccount`, `chooseLocation` or `saveField` breaks those tests**, so update the slices if you have to.
