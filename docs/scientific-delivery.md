# Scientific validation, OpenAI activation and raster delivery

14 November 2026. Frontend and account implementation are outside this work.

## Current result

| Priority | Delivered | Still limited or blocked |
|---|---|---|
| Scientific validation | Frozen engineering protocol, 21 reserved station-season evaluations, raw source hashes, per-output errors, failed gates and block-bootstrap bias intervals; technical parameter review below | Combined weather screening did not qualify. Expert agronomic review and measured crop irrigation validation remain absent. California station comparison needs CIMIS AppKey |
| OpenAI activation | Ignored local configuration loading, server-only credentials, verified model access, grounded English/Arabic rendering, crop-care evidence, bounded live-check command, explicit quota/authentication errors | Model access returned 200; generation returned `credit_balance_exhausted`. Account API credits are required before live responses can pass |
| National layers | NASA IMERG/SMAP raster context with US50 clipping and original legends/date gaps; resumable physical grid builder, COG files, point values, provenance and PNG tiles | Native valid-pixel coverage varies. The full national derived deficit grid is not precomputed; the completed live example is Kansas maize 2020, 80 cells |

## Validation protocol and interpretation

`data/catalogs/validation_protocol_v1.json` was frozen and hashed before reserved weather was downloaded.
`docs/validation/protocol-lock-v1.json` records the lock and opening timestamp. Git preserves protocol bytes.
The thresholds are explicitly provisional product screening limits, not FAO guarantees or expert-approved
irrigation tolerances. No model parameters were fitted to the evaluation results.

Temporal evaluation: AZMET Maricopa, CoAgMet Fort Collins and Kansas Hays in 2023–2025. Spatial evaluation:
AZMET Tucson, CoAgMet Akron/Greeley and Kansas Colby in 2020–2022. Each season uses 153 May–September daily
labels. There were 3,198 paired ET0 days out of 3,213 expected. Kansas timestamps are mapped to the preceding
observation day; residual civil/standard-time versus POWER LST differences remain disclosed. CoAgMet wind
heights now use the current official metadata, with historical instrument-era confirmation still pending.

Four of 21 station-seasons passed the combined gates and 17 failed. Fort Collins is diagnostic-only because
of its known site-quality concern; among the other 18, four passed and 14 failed. Eleven station-seasons
failed the rainfall-season relative-bias gate; ten failed the daily ET0 bias gate. Gates overlap. This does
not mean every ET0 calculation failed: some cases passed ET0 checks and failed rainfall. See
`validation/holdout-evaluation-v1.md` and `validation/results/holdout-evaluation-v1.json` for the full breakdown.

Seven-day chronological-block bootstrap intervals quantify within-season uncertainty in mean bias only.
They are not nationwide confidence bounds or field-level prediction intervals. The purposive seven-station
study is not a probability sample of U.S. farms. These previously reserved groups are now consumed; future
parameter tuning needs fresh untouched evaluation data. Failed gates are not relabelled as passes.

Public readiness: `GET /api/v2/validation/status`; full evaluation: `GET /api/v2/validation/holdout`.
New analysis snapshots explicitly carry the unqualified weather-screening status. Numerical FAO examples
and near-zero balance residuals still verify implementation; they do not measure weather/crop accuracy.

## Crop/soil/management technical review

| Input/assumption | Technical review | Remaining evidence needed |
|---|---|---|
| FAO Kc and growth stages | Catalog traces each value to FAO-56 Tables 11/12. Mid and late weather adjustments use the corresponding stages and expose original/limited inputs | Local hybrid/cultivar parameters and crop calendars. Fixed dates are assumptions, especially outside Great Plains/Corn Belt |
| Rooting depth | Catalog midpoint assumptions are capped by soil depth/restrictions; zero available water capacity is rejected | Measured rooting progression. Maximum depth from planting overstates early-season storage |
| Available water | Horizon-integrated SSURGO AWC includes NRCS fragment adjustments; FC–WP alternative remains a sensitivity, not a replacement truth | Field soil sampling, component heterogeneity and shallow water-table assessment |
| Runoff | NRCS curve numbers and equation are source-traced; mass conservation is checked | Local management, slope and antecedent moisture. A daily aggregate is not a resolved rainfall storm |
| Initial depletion | Explicit 0.5 TAW scenario with existing sensitivity cases | Observed planting-time soil moisture; a season does not inherit measured moisture from the previous year |
| Water stress | ETa is storage-limited and its effective Ks matches that cap; negative ET0/condensation and frozen mean-temperature conditions are excluded | Crop ET, moisture and stress observations. Single-coefficient, no-capillary-rise approximation remains |
| Net irrigation | A stated RAW-trigger/refill simulation, without application losses | Actual irrigation logs, application efficiency and management constraints; no yield/profit claim |

This is a technical source/assumption review, not a signed agronomist approval. No unsupported parameters
were changed to force a desired California irrigation total.

## California reference access

`CIMIS_APP_KEY` belongs in ignored `backend/.env`, or the server environment. The current adapter uses the
documented `StationWeb/GetDataByStationNumber` endpoint, a metric request, and the
`Ocp-Apim-Subscription-Key` header. Keys do not appear in provider URLs, exceptions or stored manifests.
The legacy query-string AppKey API is not the new adapter contract. The official current site reports a
legacy-API retirement date of 16 November 2026; verify the deployed endpoint during live testing.

Run `python tools/check_fresno_cimis.py` from `backend/` after configuring the key. It compares development
2020–2022 NASA ET0 with quality-screened published station ASCE ET0. Missing/flagged observations remain missing;
unknown units/stations/dates are rejected. This does not establish crop ET or irrigation accuracy.

Official account/key instructions and free-data statement:
https://data.ca.gov/@california-department-of-water-resources/cimis-weather-station-spatial-cimis-data-web-api

Current API documentation: https://cimis.water.ca.gov/web-api/rest-api/latest

## OpenAI configuration and activation

The user configured the private key and model. `backend/app/config.py` loads only allowlisted settings from
`backend/.env`, without variable interpolation, preserving explicit process environment values. The file is
ignored by Git. No credential value is recorded in test reports. Restart the server after changing settings.

Run `python tools/check_openai.py --live` only when ready to make up to three bounded response calls. It checks
model access, English/Arabic grounding and an injection attempt; it stops early on quota/access failures.
The latest evidence is `validation/results/openai-activation.json`. Current access succeeded, generation did
not: the service returned HTTP 429 `credit_balance_exhausted`. API credit activation is an account action.

The assistant returns server-rendered, cited evidence and immutable engine quantities. Added crop-stage
references cover maize, soybean and sorghum, with curated Arabic text. It does not invent diagnoses,
pesticide prescriptions or new numerical results. General agronomy beyond the evidence set and answer-quality
expert review remain future work. A live model-quality pass cannot be claimed while generation is blocked.

Official structured-output contract: https://developers.openai.com/api/docs/guides/structured-outputs

## National source imagery and derived COGs

`GET /api/v2/map/layers` returns the contracts for IMERG precipitation rate and SMAP L4 surface/root-zone
moisture. Exact date intervals, including gaps, come from the retrieved NASA WMTS capabilities. Unsupported
dates return 422; the backend never silently substitutes a recent image. Source legends retain original
colours/units. IMERG's unit is **mm/hour rate**, not a seasonal rainfall amount. SMAP imagery describes its
model-assimilated depth and 12:00 UTC instant; it is separate from POWER's no-data aliases.

`GET /api/v2/map/nasa/{layer}/{date}/{z}/{x}/{y}.png` fetches/caches a verified NASA PNG and combines its
original no-data alpha with the Census US50 mask. Other countries/ocean outside scope are transparent. Native
imagery can still lack pixels inside scope. Continental U.S., Alaska, Hawaii and positive-longitude Alaska
masking are checked. No quantitative value is inferred from an RGB colour. Use source numeric datasets for
quantitative analysis. Refresh allowlisted source contracts with `python tools/refresh_gibs_catalog.py`.

Derived-grid commands, from `backend/`:

```text
python tools/build_scientific_grid.py --year 2020 --crop maize_grain --plan-only
python tools/build_scientific_grid.py --year 2020 --crop maize_grain --states KS
python tools/build_scientific_grid.py --year 2020 --crop maize_grain --max-cells 100
```

Omitting states plans all 50 states, 3,557 native meteorological grid-centre points (including six Hawaii
points and 921 Alaska points). `--max-cells` bounds new work; rerunning resumes cached completed cells.
Omitting that limit processes the complete plan and makes many provider requests. It is operator-triggered,
not an anonymous public request that can launch thousands of jobs.

Every populated cell uses its own daily POWER record and cell-centre soil query. No single farm/point value
is painted over a state. Published COGs contain seasonal rainfall, ET0, crop ETc, deficit, net irrigation and
stress days. The grid is 0.5° latitude × 0.625° longitude; solar inputs remain coarser, about 1°. A finer map
does not improve this support. Cell-centre dominant soils and fixed crop calendars are disclosed scenarios.
Uncomputed, source-missing, coastal-centre and inapplicable cells remain nodata. Publication is immutable;
new coverage or values create another artifact ID, leaving old artifacts unchanged.

Live proof: Kansas maize 2020 completed 80/80 planned cells. The national derived grid remains uncomputed
outside executed scope. `validation/results/grid-build-live-check.json` records the artifact/checksum;
the actual local COG/records are in `outputs/scientific-layers/published/`. These generated datasets and
source-cache SQLite files are operator artifacts, not embedded user-account data.

Routes: `/api/v2/map/grids/{id}`, `/data.tif`, `/records`, `/{metric}/value?lon=...&lat=...`, and
`/{metric}/{z}/{x}/{y}.png`. GeoTIFFs retain floating-point quantitative values; PNGs use nearest-neighbour
resampling and the manifest's numeric legend range. Layer units/result types remain separate.

Set `FIELD_SHIFT_LAYER_DIR` to persistent writable storage. The Docker recipe uses
`/var/lib/field-shift/layers`; mount the volume there along with the database. The image includes the
scientific readiness report but no precomputed national raster. Docker runtime verification remains pending.

NASA service contract: https://nasa-gibs.github.io/gibs-api-docs/access-basics/

Source capabilities: https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/1.0.0/WMTSCapabilities.xml

## Verification

185 backend tests passed, including private literal configuration, credential redaction, quota handling, Arabic/crop evidence, immutable numerical claims, frozen gate failures, block-bootstrap repeatability, CIMIS units/QC/station checks, source alpha/date gaps, corrupted tile caches, positive-longitude Alaska/Hawaii masks, COG layout, exact values/nodata and immutable publication. Fifty raw-byte source manifests and the complete Kansas raster checksum were verified. Frontend diff is empty. One original Starlette dependency deprecation remains.
