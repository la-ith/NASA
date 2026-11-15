# Implementation status against spec v4.0

Latest full application delivery: see [full-app-delivery.md](full-app-delivery.md). The public home page, private accounts/fields, recovery, exports, saved comparisons, chat UI and selectable scientific map layers are now implemented. The all-crop national 2020 processing plan and per-metric no-data counts are recorded in `validation/results/national-grid-delivery.json`. This does not change the failed scientific qualification or establish field accuracy. OpenAI responses remain blocked by exhausted API credits. Container/cloud deployment execution remains external work.

As of 14 November 2026. Implemented means built and tested; validated means compared with independent field
observations, which has **not** been done for any output.

| Spec item | State | Evidence |
|---|---|---|
| Phase 1: U.S. forcing record, crop/soil configuration, reference calculations | Done | 2 sites × 25 years of POWER weather; SSURGO soils; FAO-56 Examples 2–35 pass |
| Phase 2: ingestion, provenance, ET0, crop demand, water balance, ≥3 strategies, JSON + report without the web | Done for 3 crops | `app/science`, `app/adapters`, `app/services`; `python -m app.cli`; 167 backend tests |
| Geography: all 50 states, Alaska antimeridian, Hawaii, outside-scope rejection | Done | `tests/test_geo.py` (15 points) |
| Historical / simulation / prediction distinction | Done | Every output carries `historical_analysis` or `conditional_simulation`; no prediction is offered |
| Phase 3: sampling study, external evaluation, error metrics | Development and frozen reserved-group weather evaluation completed; not qualified nationally | `validation/holdout-evaluation-v1.md`; 21 station-seasons; evaluation groups now consumed; crop irrigation field accuracy remains unvalidated |
| Phase 4: U.S. web app with MapLibre map, async jobs, coverage, evidence, report | Built | `frontend/` at `/`; checked in a browser for the sample and live flows. Map basemap and outlines, Alaska/Hawaii shortcuts, and forced-style-failure fallback were visually observed on 14 November 2026. Attu (52.93 N, 173.2 E) was accepted through coordinate entry; precise map-click on Attu was not certified |
| Scientific map backend | US50 NASA imagery, COG pipeline, manifests/tiles and values implemented | Six quantities; completed Kansas 2020 maize grid 80/80 cells; full national derived deficit grid is not precomputed. Frontend wiring excluded |
| Phase 5: grounded chatbot | English/Arabic cited evidence backend; model access verified; live generation blocked by exhausted API credits | Strict evidence IDs, source-rendered crop-care/analysis claims, private conversations, limits/fallback. Expert agronomy review and frontend wiring remain pending |
| Phase 6: Palestine | Not started; the Hebron v3 prototype (`/v1/`, `/api/v1`) was retired on 2026-11-15 | — |
| USDA CDL | Classified point adapter implemented | USDA CroplandCROS year-locked rasters; CONUS live check succeeded; separate Hawaii service is year-dependent; Alaska unsupported; never auto-confirmed as farmer history |
| IMERG and SMAP | Source-checked context adapters via POWER UTC | IMERG live probe 3/3 valid days; SMAP probe 0/6 values, correctly `no_data`; direct Earthdata SMAP L4 ingestion pending |
| PRISM and optional imagery/other sources | Pending | Existing station development comparison remains the external evaluation baseline |
| Agronomic review of crop parameters and rotation notes | Not done | Labelled draft-unreviewed in every result |

## Known issues to investigate in Phase 3

- Fresno, CA (irrigated maize, live run): median net irrigation 1,066 mm per season looks high next to published
  Central Valley corn water use. Possible causes: POWER grid weather, the Kc climate adjustment in very dry air,
  the 150-day stage lengths, or the refill rule. Compare with CIMIS station ET0 before trusting California values.
- TAW differs strongly between NRCS awc_r and θ(1/3 bar) - θ(15 bar); both are reported.

## Review follow-through — engine 2.1.0

FS-001–FS-007 are addressed: shared demand preparation; pure computation in two worker threads with a 16-job admission limit; calendar/history/decision-year validation; session ownership for jobs/results/reports; a documented late-stage Kc regression correction; stale coverage-response protection. Existing unowned v2 rows are preserved but inaccessible through private result routes. Shutdown/restart states are explicit. No database connection is used by simulation workers.

Verification: 140 backend tests passed and one frontend out-of-order-response test passed. One dependency deprecation warning remains. Numerical verification is separate from field validation. Reference stations are evaluation-only sources; no new production dataset, crop, chatbot, Palestine or frontend redesign was added.

Fresno remains unresolved pending an appropriate California reference. Remaining limitations: initial soil state and fixed rooting depth, station-era wind/siting metadata, daily observation-window alignment, agronomic review, and output-specific acceptance thresholds before opening holdouts. This remains a single-instance prototype, not a certified distributed job service.

## Backend follow-through — engine 2.2.0

See `backend-handoff.md` for endpoint contracts, configuration and precise remaining scope. Frontend files and
user-account implementation were left unchanged for the user's separate work. SQLite additions store source
artifacts, conversations and daily API usage only; they do not introduce login or an account database.

Added immutable what-if scenarios with parent links; paired common-year comparisons; time series, original weather
exports and provenance routes; point layer manifests/GeoJSON; bounded supplemental source queries; private
OpenAI evidence selection and local fallback. Original source cache records now preserve each request/retrieval
even when the provider returns identical content, allowing the 30-day cache to refresh correctly.

Scientific changes: negative ET0/condensation and zero root capacity are outside applicability; storage-capped ET
reduces effective Ks/stress reporting; excluded requested seasons imply partial status; standard ETc is correctly
labelled conditional simulation; per-season Kc climate limiting is exposed. Results include a distinct scientific
validation state, including the unresolved California discrepancy.

The evaluation had a confirmed Kansas date-label bug: daily midnight stamps describe the previous day. This was
corrected according to the provider, including the download end date. Hays daily ET0 RMSE is now 0.731, 0.962,
0.794 mm/day for 2020–2022 (previously 1.726, 1.916, 2.258). The decrease follows an evaluation correction;
it is not a calibrated improvement in POWER data or proof of field irrigation accuracy. Sub-day observation-window
differences remain. Held-out station/weather groups remain unused.

Verification: **167 backend tests passed**, including 27 new extension/integrity/AI tests. One existing Starlette
dependency deprecation warning remains. Live checks retained raw source artifacts and hashes in
`data/validation/raw/backend_*.json`; summary: `validation/results/backend-source-checks.json`. A full Hays 2020
live POWER/SSURGO replay succeeded. OpenAI failure/grounding paths were mocked and tested; no live AI call was
made because a key/model is not configured. Docker recipe prepared; Docker is unavailable for image testing.

Offline CLI smoke test: complete 25-season/three-strategy Hays replay, engine 2.2.0, largest water-balance
residual 6.96e-13 mm. Verified 25 saved source manifest/content hashes. Frontend diff is empty.

Remaining work includes frontend integration, user accounts, national rasters/tiles, expanded crop-care retrieval
and expert review, direct SMAP access with confirmed coverage, California reference validation, and optional
datasets/Palestine. No nationwide accuracy or complete spec-v4 release is claimed.


## First-three-priority follow-through — 14 November 2026

- Scientific study: froze `data/catalogs/validation_protocol_v1.json` before opening reserved weather, retained a hash/timestamp lock, then evaluated 21 station-seasons from seven stations. Four passed the combined provisional weather gates and 17 failed; FTC01 remains diagnostic-only because of known siting concerns. The 18 eligible station-seasons did not qualify nationally. No parameters were fitted to those results. The groups are now consumed, not untouched future tests. See `validation/holdout-evaluation-v1.md` and the full JSON for separate rainfall/ET0 gates, missingness and seven-day block-bootstrap bias intervals.
- OpenAI: private ignored `.env` loading implemented, preserving process environment precedence. The supplied key can access `gpt-6-luna` (model endpoint HTTP 200), but response generation returned HTTP 429 `credit_balance_exhausted`. Live activation is **blocked by account credits**, not missing configuration. English/Arabic evidence rendering, crop-stage care references, grounding checks and quota/access failure states are implemented; no live response success is claimed.
- Map backend: three allowlisted NASA GIBS imagery layers (IMERG rate and SMAP surface/root-zone moisture), exact date intervals/gaps, source legends/units and US50 alpha masking. Live source tiles passed over Kansas, Alaska and Hawaii; positive-longitude Alaska masking is tested. Source imagery does not supply quantitative values by colour inversion.
- Derived rasters: resumable per-cell daily NASA POWER + SSURGO scenarios, six-band COG publication, immutable manifests, provenance records, point queries and PNG tiles. National plan: 3,557 land-centre climate cells. Completed live Kansas 2020 maize example: 80/80 cells. **National deficit values are not all precomputed.** Uncomputed/unsupported cells are nodata. Cell-centre soils and fixed crop calendars are exploratory scenario assumptions, not field measurements.
- California: current header-authenticated CIMIS adapter and a development-only Fresno comparison runner prepared. Station access still requires a private CIMIS AppKey. API keys never enter provider URLs or source manifests. No human agronomist or measured crop irrigation validation is claimed.

Frontend and user-account implementation remain unchanged. Docker image build/runtime verification remains pending on a host with Docker.

Verification for this delivery: 185 backend tests pass, including 18 new validation/configuration/AI/raster tests. Original dependency deprecation remains; no frontend files changed. Fifty raw-byte download manifests and the live Kansas COG checksum were verified. API 2.3.0 retains physical engine 2.2.0.

## CIMIS key activation follow-through

CIMIS credentials were configured privately and accepted by the current API. The previously blocked Fresno comparison now succeeds for 2020–2022. Live response solar units `(W/m²)` are explicitly normalized with the same physical conversion as `(W/sq.m)`; raw units/payloads remain unchanged. A regression test verifies the real-response conversion.

Paired daily ET0 bias (NASA minus CIMIS ASCE): +0.692, +0.868, +0.436 mm/day; RMSE: 1.098, 1.145, 0.890. Unflagged paired counts: 145, 149, 152 of 153; 2020 is below the 95% day threshold. Station metadata and component errors are retained. See `validation/fresno-cimis-comparison.md`. This is a successful reference comparison, not confirmation of the 25-season irrigation estimate or measured field accuracy.

Remaining: scientific qualification/expert review and field observations; OpenAI response generation last failed because API credits were exhausted; national derived deficit grid outside executed scope; frontend/account work; deployment verification. CIMIS key configuration is no longer outstanding.

Verification after CIMIS activation: 186 backend tests pass, with one existing dependency deprecation. No frontend files or account database were changed. Private credentials remain ignored and excluded from artifacts.
