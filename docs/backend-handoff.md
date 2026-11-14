# Backend handoff — engine/API 2.2.0

14 November 2026. Frontend and user-account implementation are outside this change. The backend now provides
data ingestion, historical replay, immutable results, private point layers, scenario comparisons, supplemental
source queries and a bounded OpenAI assistant integration. This is a single-instance development backend.

## Run and configure

From `backend/`, install `requirements.txt` and run `uvicorn app.main:app --host 127.0.0.1 --port 8000`.
The generated OpenAPI contract is at `/openapi.json`, with interactive documentation at `/docs`.
Legacy startup network warmup is off by default. `FIELD_SHIFT_DB` selects the persistent SQLite file.
The service reads process environment variables; `.env.example` is a configuration reference and is not
automatically loaded. Never put a provider key in browser code, source control, URLs or client requests.

For AI, set `OPENAI_API_KEY` and `OPENAI_MODEL` privately in the server environment. Both are required; no
model or paid account is assumed. `/api/v2/chat/status` reports configuration presence only. It does not
verify credentials or model access. `FIELD_SHIFT_AI_DAILY_CALL_LIMIT` defaults to 50 attempted API calls per
UTC day across this database; token output is bounded at 800 and messages at 4,000 characters. Test failures
and service failures count toward the attempt budget. There are at most 10 conversations per browser owner
and 20 question/response exchanges per conversation. Deleting a conversation does not reset daily usage.

Docker preparation: from the repository root run
`docker build -f backend/Dockerfile -t field-shift-backend .`, then run with a persistent volume mounted at
`/var/lib/field-shift` and private environment injection. The image intentionally contains the backend and
required data only. Docker is unavailable in this workspace, so image build/runtime verification is pending.
Use a single Uvicorn worker. Multiple processes need a durable job queue, database coordination and distributed
admission/rate limits; adding workers to the current image is unsupported.

## Contracts for the future frontend

| Operation | Route | Meaning |
|---|---|---|
| Check a location | `POST /api/v2/coverage` | Scope and per-source checks; `unchecked` is not confirmed coverage |
| Product discovery | `GET /api/v2/sources`, `GET /api/v2/products` | Scientific forcing versus supplemental context |
| Start analysis | `POST /api/v2/analyses` | Returns 202 and a job status URL; `mode` must explicitly be `live` or `sample` |
| Poll | `GET /api/v2/jobs/{job_id}` | `queued`, `running`, `succeeded` or `failed`; terminal failures carry stage/retryability |
| Read snapshot | `GET /api/v2/analyses/{id}` | Immutable result with seasons, exclusions, source versions, assumptions and validation status |
| Read report | `GET /api/v2/analyses/{id}/report` | Markdown report generated from that snapshot |
| Read evidence | `GET /api/v2/analyses/{id}/provenance` | Equations, source manifests, input provenance, validation limits |
| Weather export | `GET /api/v2/analyses/{id}/weather` | Exact original JSON payload used, verified against its canonical content hash; never a fresh replacement |
| Chart data | `GET /api/v2/analyses/{id}/timeseries` | Per-strategy, per-season values and excluded-season reasons |
| Layer catalog | `GET /api/v2/analyses/{id}/layers` | Private point-supported manifests, units, period, source support and GeoJSON URLs |
| Layer value | `GET /api/v2/analyses/{id}/layers/{layer_id}/geojson?year=2020` | Generalized display point; omit year for median; unavailable values are null |
| Compare | `POST /api/v2/analyses/{id}/compare` | Body: `strategy_a`, `strategy_b`, `metric`; paired A−B differences using common years only |
| What-if | `POST /api/v2/analyses/{id}/scenarios` | Body: `changes`; creates a new job/result linked by `parent_analysis_id`; parent stays immutable |
| IMERG/SMAP | `POST /api/v2/products/{product}/query` | Body: `lat`, `lon`, ISO `start`, `end`; past interval ≤366 days |
| Crop classification | `POST /api/v2/products/usda_cdl/point` | Body: `lat`, `lon`, `year`; 2008 through the last complete year, subject to regional service availability |
| Source artifact | `GET /api/v2/products/records/{artifact_id}` | Owner-scoped original and normalized supplemental result |
| Start conversation | `POST /api/v2/chat/sessions` | Optional `analysis_id`; each conversation binds to that immutable analysis |
| Ask | `POST /api/v2/chat/sessions/{session_id}/messages` | Body: `message`; returns response mode, server-rendered evidence/citations and limitations |
| Read/delete conversation | `GET` / `DELETE /api/v2/chat/sessions/{session_id}` | Owner-scoped history and deletion |

Scenario changes may include goal, current practice, crop candidates, planting dates, initial depletion,
soil override and irrigation description. Existing analysis behavior always computes both rain-fed and
irrigated scenarios; the irrigation description records practice and is not a new trigger/refill policy.
Field coordinates, source mode and evaluation period cannot change through this convenience route; start a
fresh analysis for those changes. Crop/soil inputs still pass the normal request validation.

The future frontend must preserve the HttpOnly `field_shift_session` cookie on requests. Results, reports,
chat and artifacts belong to the cookie's hashed owner. A new browser/session cannot read old private IDs.
There is no user login, password storage, farm ownership model, account recovery or sharing permission yet.
Changing the selected field should create/select the conversation for the matching analysis; it must not
silently reuse the previous analysis context. No CORS cross-origin deployment is configured.

## Map data limits

Available point layers: seasonal precipitation, ET0, standard ETc, rain-fed deficit, net irrigation and stress
days for each simulated crop. Values, legends and periods come from the saved result. Unknown years return
null. A detailed basemap cannot improve NASA/soil data resolution. Generalized point geometry is for display.

This change does **not** create national deficit rasters, interpolated surfaces, vector/raster tiles, COG
processing or nationwide field predictions. Those require a separately specified gridded pipeline, source
QA and a tile server. Do not fill a national heatmap from a single selected-point result. Supplemental
queries retain their own UTC period, depth and product provenance and do not change the LST water balance.

## OpenAI behavior and verification

The integration calls the OpenAI Responses API with `store: false` and strict JSON-schema output. The model
can select approved evidence IDs and missing-information questions. The server renders the evidence text,
citations and immutable analysis numbers. The model has no arbitrary tools, calculations, dataset writes,
field mutations, diagnosis or pesticide-prescribing capability. Analysis coordinates are not included in
the model evidence package. User-entered question text and up to four prior questions are sent.

This is an evidence-selection assistant baseline, not a complete free-form agronomy adviser. Its curated
references cover FAO-56 water demand/balance and NASA gridded data. Expanded crop-care retrieval, Arabic
answer wording, expert review and conversational quality evaluation remain future work. No claim of live
OpenAI success is made without a real configured key/model. Configuration absence, refusal, malformed output,
invented IDs, additional generated claims, incomplete responses and service errors use a clearly labelled
deterministic fallback. The daily budget limit returns 429; the analysis APIs remain independent of AI.

Primary API contract: https://developers.openai.com/api/reference/resources/responses/methods/create

## Scientific checks and remaining gates

1. Numerical verification: published FAO-56 examples, source-unit checks, water conservation, impossible-input
   rejection and fixed-source regressions. Storage-limited ET now also reduces reported effective Ks and
   stress-day accounting. Negative ET0/condensation and zero root-zone capacity are outside applicability.
2. Reporting: ETc is conditional simulation, not an observed historical quantity. Any excluded requested
   season makes a result partial. Results expose field-validation status and a California warning.
3. Transparency: per-season `kc_climate_qa` records original/used stage wind and RHmin and applicability-range
   limiting. Those limits are FAO method limits, not fitted error corrections.
4. Corrected evaluation: Kansas daily stamps belong to the preceding day according to the official provider.
   The download interval now includes October 1 to cover September 30. New diagnostic Hays RMSE is
   0.731/0.962/0.794 mm/day for 2020/2021/2022. This corrects the comparison, not the NASA source observations.
   Exact sub-day windows, station-era metadata and CoAgMet site suitability still need review.
5. Live source checks: `validation/results/backend-source-checks.json` and hash-verified originals in
   `data/validation/raw/backend_*.json`. Hays 2020 POWER has 366 days with all nine variables present;
   SSURGO and all three crop simulations ran. IMERG had 3/3 valid daily values. SMAP had 0/6 valid values.
   USDA Hays 2020 classified the pixel as Grassland/Pasture, demonstrating why demo crop history is a
   separate assumed/farmer input. Hawaii 2020 had no matching raster in its separate service.

There is **no certified nationwide or field irrigation accuracy**. Fresno's high irrigation estimate remains
unresolved pending California reference observations (registered CIMIS access was unavailable). Crop parameters,
calendars, initial moisture and fixed rooting depth need agronomic review. Define output-specific acceptance
thresholds before evaluating held-out station/season groups. No holdout weather/station data was used here.

Optional imagery, PRISM ingestion, national tiles, direct Earthdata SMAP L4 ingestion, account databases and
Palestine are not complete. SMAP through POWER is strictly source-checked and must not silently become a
MERRA-2 moisture product. API-key setup is needed for live OpenAI responses. These are explicit remaining
items, rather than completed/validated features.

## Reproduce verification

From `backend/`:

```text
python -m pytest -q
python tools/run_pilot_validation.py
python tools/check_backend_sources.py
python -m app.cli --site ks_hays
```

The test suite is offline. The pilot runner reuses hash-verified raw artifacts and evaluates development
years only; live source probes call providers and retain original payloads. Live availability may change.
