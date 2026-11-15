# Field Shift API contracts for the browser

These shapes are taken from `backend/app/api/*.py` and `data/fixtures/showcase_ks_hays.json` (API 2.3.0). If anything here disagrees with the code, the code wins: re-check the route before relying on a field.

All endpoints are same-origin under `/api/v2`. Cookies carry identity: `field_shift_session` is anonymous, and an account cookie identifies a signed-in user. The server rejects cross-origin POST, PUT, PATCH and DELETE requests with 403.

## Contents
1. Error shapes
2. Reference data
3. Location coverage
4. Analyses (async jobs)
5. Analysis result shape
6. Follow-ups on an analysis
7. Map layers and products
8. Chat
9. Accounts and fields
10. Validation and showcase

## 1. Error shapes
- 422 validation: `{"error":{"code":"invalid_input","fields":[{loc,msg,type,...}]}}`
- Provider or data failure (502): `{"error":{"code":"provider_error"|<integrity code>,"message":...,"sample_available":true}}`. When `sample_available` is true, offer a run with `mode:"sample"`, labelled as saved data.
- Custom errors: `{"error":{"code","message","stage","retryable"}}`. Examples: `outside_scope` (422) and `queue_full` (503, retryable).
- FastAPI `HTTPException`: `{"detail":"..."}`, for example 404 "analysis not found" or 429 "session limit reached".

`getJSON` in `app.js` already turns all of these into `Error.message`.

## 2. Reference data
- `GET /api/v2/crops`: the crop catalog. The workspace keeps it in `catalog.crops[].id`, for example `maize_grain`, `soybean` and `sorghum_grain`.
- `GET /api/v2/boundaries`: GeoJSON for the 50 states.
- `GET /api/v2/equations`: `{id: {formula, unit, reference}}`, shown on `/science/`.
- `GET /api/v2/sources`: data source register.
- `GET /api/v2/health`

## 3. Location coverage
`POST /api/v2/coverage` with body `{lat, lon, mode?: "live"|"sample"}`.
- Outside the 50 states: `{in_scope:false, state:null, reason}`.
- Inside: `{in_scope:true, state:{code,name}, demo_site, products:{nasa_power, ssurgo, usda_cdl, gpm_imerg, smap}}`.
  - Each product is `{status, reason, ...}`.
  - `status` is one of supported, partial, unknown, unsupported or **unchecked**. `unchecked` means "not verified": never show it as covered.
  - Map coverage is not a promise of analytical coverage.

## 4. Analyses (async jobs)
`POST /api/v2/analyses` returns **202** with `{job_id, state:"queued", status_url:"/api/v2/jobs/{id}"}`.

Request body (`AnalysisRequestV2`):

| Field | Rule |
|---|---|
| `mode` | **required**, `"live"` or `"sample"` |
| `lat`, `lon` | must fall in one of the 50 states |
| `start_year`..`end_year` | 1981 to the last complete year, at most 40 seasons; the UI uses the last 25 seasons from 2001 |
| `decision_year` | |
| `goal` | `conserve_water`, `reduce_drought_stress` or `improve_soil_rotation` |
| `irrigation` | `rain-fed`, `irrigated` or `unknown` |
| `history` | up to 10 items `{year, crop, provenance:"farmer"|"team"|"cdl"}` |
| `current_practice` | |
| `candidates` | up to 6 crop ids |
| `planting_dates` | `{crop: "MM-DD"}` |
| `initial_depletion_fraction` | 0–1 |
| `soil` | `{awc_mm_per_m, depth_cm, hydrologic_group A-D}` |
| `parent_analysis_id` | |
| `field_id` | requires sign-in, and lat/lon must match the saved field to 4 decimal places |

`GET /api/v2/jobs/{job_id}` returns `{job_id, state, stage, updated_utc, analysis_id?, analysis_url?, error?}`.
- `state` is `queued`, `running`, `succeeded` or `failed`.
- `stage` is `queued`, `retrieving_weather`, `retrieving_soil`, `simulating`, `saving` or `done`. Map these to friendly text and never show raw ids.
- `error` is `{code, stage, message, retryable}`.

Poll about every 900 ms. Stop polling if the user signs out (the `authVersion` guard).

## 5. Analysis result shape
`GET /api/v2/analyses/{id}` returns these top-level keys:
`schema_version, decision_year, status, mode, result_types, location, period, goal, output_order, summary, strategies, rejected, soil, inputs, limitations, provenance, versions, validation, equations, generated`

`strategies[]` items:
- `id`, `crop`, `role`, `name`, `planting`, `why_included`, `rotation`, `parameters`.
- `result`:
  - `taw_mm`, `taw_fc_wp_mm`, `raw_mm`, `root_depth_m`, `seasons_simulated`, `seasons_excluded`, `max_closure_residual_mm`.
  - `summary.{et0, etc_standard, precipitation, rainfed_eta, rainfed_deficit, rainfed_stress_days, irrigated_net_irrigation}`. Each is `{unit:"mm per season", result_type:"conditional_simulation", spread:{n, mean, p10, median, p90, minimum, maximum}}`.
  - `seasons[]`: `{year, planting, harvest, et0, etc_standard, precipitation, runoff, rainfed_eta, rainfed_deficit, rainfed_stress_days, rainfed_drainage, irrigated_net_irrigation, irrigated_events, kc_mid_adjusted, kc_end_adjusted, max_closure_residual, kc_climate_qa}`.
- `result` may be `null`, for example when soil is missing. In that case the UI shows "Not available" (see `metricValue`).

Display rules:
- Show the backend's `median` (with p10–p90 if there's room) and the unit.
- Never recompute numbers from `seasons`.
- Show `rejected` strategies with their reason, and show `limitations`.
- `result_type` "conditional_simulation" means historical replay under stated assumptions.

`GET /api/v2/analyses/{id}/report` returns a plain-text report.

## 6. Follow-ups on an analysis
- `GET .../timeseries` returns `{period, result_types, strategies:[{id, crop, seasons, exclusions}]}`.
- `GET .../provenance` returns `{provenance, versions, equations, inputs, limitations, scientific_validation}`.
- `GET .../weather` returns daily weather used.
- `POST .../compare` takes `{strategy_a, strategy_b, metric}`. An unknown strategy or metric gives 422.
- `POST .../scenarios` takes `{changes}` and returns 202 with a new job. Allowed keys are goal, current_practice, candidates, planting_dates, initial_depletion_fraction, soil and irrigation.
- `GET .../layers` and `GET .../layers/{layer_id}/geojson?year=`.

## 7. Map layers and products
Under `/api/v2/map`:
- `GET /layers` returns `{source_layers[], derived_grids[]}`. Grids have `schema "grid-cog-1.0"`, `coverage.complete` and `job.states`.
- `GET /nasa/{layer_id}/{day}/{z}/{x}/{y}.png`: GIBS imagery, display only.
- `GET /grids/{artifact_id}`, `/records`, `/data.tif`, `/{metric}/value?lat&lon` (the actual number), and `/{metric}/{z}/{x}/{y}.png` (tiles).
- `GET /build-status`

Always read values from `/value`, never from tile colours.

Under `/api/v2/products`:
- `GET ''`
- `POST /usda_cdl/point`
- `POST /{product}/query` — `product` is `gpm_imerg`, `smap` (SFMC/RZMC, m³/m³; POWER currently returns no values) or `merra2_soil_wetness` (GWETTOP/GWETROOT, 0–1 wetness, MERRA-2). Show SMAP and MERRA-2 as separate, labelled values; never merge or relabel them.
- `GET /records/{artifact_id}`

These are context products. Crop history stays user-entered.

## 8. Chat
Under `/api/v2/chat`. The server holds the provider key.
- `GET /status`
- `GET /sessions` returns `{sessions:[{session_id, analysis_id, created_utc}]}`.
- `POST /sessions` takes `{analysis_id?}` and returns 201 `{session_id, analysis_id}`. Each owner can have at most 10 sessions (429).
- `POST /sessions/{sid}/messages` takes `{message (1–4000 chars), language?: "auto"|"en"|"ar"}` and returns the answer object. Each session holds at most 20 messages, and a daily AI budget applies. When either limit is hit you get 429; say "analysis remains available".
- `GET /sessions/{sid}` and `DELETE /sessions/{sid}` (204).

The assistant explains evidence from the analysis. It does not calculate. Render its text with `esc()`.

## 9. Accounts and fields
- `GET /api/v2/auth/me`
- `POST /auth/register` takes `{name, email, password}` and returns 201 with `{user, recovery_code}`. Show the recovery code once.
- `POST /auth/login` and `POST /auth/logout` (204).
- `POST /auth/recover`
- `DELETE /auth/account` (204).
- `GET /fields`, `POST /fields` (201), `PUT /fields/{id}` and `DELETE /fields/{id}` (204).
- `GET /account/analyses` and `GET /account/export`.

After sign-in or sign-out, increment `authVersion` and clear `fields`, `activeField`, `currentAnalysis` and `chatSession`.

## 10. Validation and showcase
- `GET /api/v2/validation/status` returns fields such as `field_irrigation_accuracy`, `numerical_verification`, `engineering_weather_screening`, `california_status`, `california` and `expert_review`. Display them verbatim; don't upgrade the wording.
- `GET /api/v2/validation/holdout`
- `GET /api/v2/showcase` returns the saved Hays, KS analysis (the same shape as §5). The landing page and the demo use it. Always label it as a saved example or historical replay.
