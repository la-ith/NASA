# Field Shift — Product and Analysis Specification

> Superseded by [Field Shift Final Implementation Specification v4.0](Field%20Shift%20Product%20Spec%20v4_0.md), which includes the approved interactive map and grounded agricultural AI assistant. Keep this file as a historical planning reference.

Version 3.3 | 14 November 2026 | NASA Space Apps Challenge 2026

## 1. Status and decisions

This is the current product and implementation plan. It supersedes v3.2 where scope, scientific methods, data contracts, delivery order, or geography differ. Preserve v3.2 as the historical specification of the Hebron prototype; its code listings, pilot measurements and expected results are not the specification or validation evidence for the U.S. system.

User-confirmed decisions:

- Primary geography: the United States, all 50 states including Alaska and Hawaii.
- Build and validate the data-analysis and outcome-estimation system first. Build or adapt the web interface after the backend milestone passes.
- Use relevant NASA environmental data and available U.S. agricultural reference data. The 24 challenge resources are a source catalog, not a requirement to integrate every source.
- Ground numerical analysis in documented physical equations and explicit mathematical methods.
- Palestine is an optional extension only after the U.S. analysis and web milestones, if time remains. Use only products that cover the selected Palestinian location.
- Global operation and support for most plants are no longer the immediate delivery scope. Keep adapters and crop profiles extensible.

Implementation status: this document changes the plan, not the application. Repository inspection confirms existing backend, frontend and test files from the earlier prototype. v3.2 reports implemented Hebron features; this revision does not re-run or certify those claims. U.S. coverage, new scientific calculations and predictive performance remain planned until demonstrated and tested.

## 2. Vision and primary outcome

Field Shift helps U.S. farmers and advisors compare at least three agricultural rotation strategies, including current practice, using environmental data, soil properties, crop characteristics and farmer priorities.

For each strategy, show why it was included, expected effects under stated conditions, benefits, supporting evidence, missing information, uncertainty and risks requiring local review. The farmer makes the decision.

The central deliverable is a reproducible analysis package: input snapshot, validated source records, equations, parameter versions, calculated outputs, validation results and a machine-readable report. The web app presents this package.

No yield, profit, soil-health improvement or water saving is guaranteed. Do not attach numerical effects to rotation rules unless a suitable model and evidence support them.

## 3. Geographic scope and spatial contract

### United States release

- Display all 50 states on the web map, with usable navigation to Alaska and Hawaii, including locations near the antimeridian.
- Accept analysis locations inside the agreed 50-state boundary dataset. U.S. territories are outside this release unless explicitly added in a later decision.
- Before the web exists, enforce the same geography through CLI and API validation.
- Validate land/field applicability separately from national boundaries; ocean points do not become valid farms because they fall inside a broad map bounding box.
- Use point-in-polygon checks against versioned boundaries, not one rectangular longitude/latitude test.
- Show coverage per product, variable, date and location. Map coverage is not a guarantee of analytical coverage.
- If essential evidence is missing, return a partial or unsupported analysis with a precise reason. Never silently replace a location with a nearby supported farm.

### Precision and privacy

Remove the v3.2 requirement to round all coordinates to 0.1 degrees. That rule was specific to the coarse Hebron POWER case and is unsuitable for finer soil and crop layers.

Keep analysis geometry at the precision needed by the selected datasets, with restricted access. Generalize coordinates in public links, logs and shared reports by default. Record requested geometry separately from returned grid cells, soil map units and pixel footprints.

Match data by documented spatial support. Resampling a coarse layer onto a finer grid does not create field-scale information. Soil map units can contain several components; record the selection or aggregation method and uncertainty.

## 4. Source catalog and integration priorities

Use the official challenge Resources tab as the catalog. Confirm access, licensing, variable definitions, current product version, geographic footprint, temporal coverage and quality flags before promoting an adapter.

| Priority | Source | Role | Important qualification |
|---|---|---|---|
| Core | NASA POWER | Historical temperature, humidity, wind, solar radiation and precipitation inputs | Verify units and resolution per variable; regional estimates are not field measurements |
| Core reference | WSS / SSURGO, with STATSGO2 only as a documented coarser fallback | Soil texture, available water properties and relevant restrictions | WSS is an access interface to soil information, not an independent second observation; check actual survey coverage |
| Core agricultural context | USDA CDL / CroplandCROS | Crop classification and candidate history evidence | Retain classification provenance; do not equate a classified pixel with farmer-confirmed history; Hawaii has a separate product and Alaska availability must be checked |
| Verification | PRISM and suitable independent ground observations | Climate comparison and bias assessment where covered | Do not assume PRISM covers all 50 states or is a direct station record; document dependence between references and source products |
| Next, after core | GPM IMERG | Alternative precipitation estimates and temporal rainfall analysis | Verify run/version, quality, latency and overlapping periods; do not combine its shorter record with POWER without an explicit method |
| Next, after core | SMAP | Soil-moisture context and possible model checking | Modelled root-zone products differ from surface retrievals; grid-average moisture is not direct field-root-zone storage |
| Optional | Landsat or MODIS/VIIRS; Sentinel-2 where useful | Vegetation and bare-ground context | QA/cloud masks, valid observations and pixel support required; indices alone do not establish crop species or disease |
| Optional | ECOSTRESS / OpenET | ET comparison and stress context | Select the exact ET quantity and footprint; model-derived ET is not automatically ground truth |
| Optional | SRTM or another verified elevation product | Elevation, slope and terrain context | SRTM does not cover most of Alaska; use a verified covering alternative or mark unavailable |
| Optional | GAEZ, GLDAS, ERA5, NLDAS | Suitability context or additional model/reference inputs | State provider and coverage; GAEZ/ERA5 are not NASA, NLDAS is regional and each model has limitations |
| Optional | QuickStats, USDA Market News, NAIP, NLCD, LANDFIRE, GEDI, CoCoRaHS, NWIS, Ag Data Commons | Statistics, markets, imagery, ecosystems, hydrology or research evidence | Integrate only for a defined output; availability is location-, date- and dataset-specific |

The minimum operational pipeline uses NASA weather inputs, a documented crop profile, a seasonal calendar, and the soil/management inputs required by the requested calculation. Missing soil or irrigation inputs can limit the output to climate and crop-demand context.

Do not require every optional adapter before delivering a working analysis. U.S.-wide requests may return different levels of detail based on evidence.

## 5. Scientific analysis contract

Every numerical output records equation ID, reference, input variables and units, parameter sources, applicability, assumptions, quality status, processing version and uncertainty method. Every rule records its geographic and crop scope and review state.

### 5.1 Reference evapotranspiration

Use the daily FAO-56 Penman–Monteith method:

ET0 = [0.408 Delta (Rn - G) + gamma (900 / (T + 273)) u2 (es - ea)] / [Delta + gamma (1 + 0.34 u2)]

- ET0: reference evapotranspiration, mm/day.
- Rn and G: net radiation and soil heat flux, MJ/m²/day.
- T: mean air temperature, degrees Celsius.
- u2: wind speed at 2 m, m/s.
- es and ea: saturation and actual vapour pressure, kPa.
- Delta: saturation vapour-pressure curve slope, kPa/degree Celsius.
- gamma: psychrometric constant, kPa/degree Celsius.

Implement the FAO-56 supporting equations and documented daily assumptions. Incoming shortwave radiation is not Rn; calculate net radiation. Handle wind measurement height, humidity availability, elevation/pressure, dates and latitude explicitly. Verify NASA response units before any derived unit conversions. Missing indispensable inputs yield unavailable status unless a separately documented fallback method is selected and disclosed.

### 5.2 Crop demand

ETc_standard(t) = Kc(t) * ET0(t)

Use sourced, crop- and stage-specific Kc profiles and a local crop calendar. ETc_standard represents non-stressed demand under its stated assumptions, not observed consumption or a promise of yield. Planting date, stage durations and root development are explicit inputs or disclosed defaults.

For a first implementation use one documented FAO-56 crop-coefficient approach consistently. Add stress adjustment only with the associated water-balance method. Do not mix single- and dual-coefficient equations without defining evaporation and transpiration separately.

### 5.3 Daily root-zone water balance

For a fixed control volume, express the balance in mm per daily timestep:

S(t) - S(t-1) = P(t) + I_net(t) + C(t) - R(t) - D(t) - ETa(t)

S is root-zone water storage; P precipitation; I_net net irrigation entering the control volume; C upward capillary flow; R runoff; D deep drainage; ETa actual evapotranspiration. Snow accumulation/melt must be represented when applicable, or the affected season is outside model applicability. Frozen-soil conditions also require treatment or an unavailable result.

Define initial storage, soil layers, runoff/infiltration, drainage, irrigation efficiency, capillary rise and ET stress method. Gross irrigation is converted to net irrigation once; never deduct the same loss twice. Do not substitute effective rainfall for P while also subtracting the same runoff/drainage losses.

Available water capacity for a homogeneous root zone:

TAW = 1000 * (theta_FC - theta_WP) * Zr

RAW = p * TAW

theta_FC and theta_WP are volumetric field-capacity and wilting-point water contents in m³/m³; Zr is rooting depth in m; p is the sourced depletion fraction; TAW and RAW are mm. For layered soils, integrate appropriate properties by layer instead of assuming one homogeneous profile.

If roots grow, account for water entering the expanding control volume. Check storage limits and water-balance closure; do not clip storage values in a way that hides unaccounted fluxes.

Outputs may include standard crop demand, simulated actual ET, storage, depletion, stress duration and net irrigation requirements under explicit management assumptions. Water not supplied in a rain-fed scenario remains a simulated deficit, not automatically applied irrigation.

### 5.4 Climate and thermal indicators

Calculate historical seasonal rainfall, coverage, baseline means, anomalies and variability from validated observations. Use season dates appropriate to the crop and location; remove the universal October–May season and fixed 2026/27 candidate season.

If adding growing degree days, select and version the crop-specific method, base temperature and any upper cap. If adding frost/heat indicators, use reviewed crop-stage thresholds. Report historical exposure, not expected plant damage without a suitable response model.

### 5.5 Rotation and soil criteria

Evaluate crop family, preceding crops, continuity of known history, management and regional applicability. Preserve unknown seasons and conflicting sources. Local expert-reviewed rules support qualitative rotation comparisons.

Retire the assumption that the same three Hebron crops and R1–R6 labels are valid throughout the United States. Do not claim a quantified nitrogen credit, soil-carbon gain, erosion reduction, yield increase or pest reduction from a generic legume/cereal rule.

## 6. Analysis, prediction and scenario outputs

Distinguish three result types in the API, report and later UI:

| Type | Meaning | Required evidence |
|---|---|---|
| Historical analysis | Indicators calculated from past data | Validated record, period and calculation |
| Conditional simulation | Crop/soil response estimated under a supplied weather and management scenario | Physical model, parameter provenance, initial conditions and applicability |
| Validated predictive estimate | A model estimates an explicitly defined future target/horizon | Training or calibration provenance, independent testing, a baseline comparison and uncertainty assessment |

Initial outcome estimation uses historical weather replay: run each candidate under the same complete historical seasons and management assumptions. Report the distribution of simulated demand, deficits and stress, including its available-season count. This is a historical scenario ensemble; it is not a next-season weather forecast or a calibrated probability of crop success.

Predictive models are enabled target by target only after validation. Define target, units, prediction date, horizon, available-at-prediction-time inputs and applicable population before development. Evaluate against a simple baseline using held-out locations and later periods. A future weather sequence needs an identified forecast/scenario source; historical NASA observations alone do not supply one.

Weather uncertainty, parameter uncertainty and model discrepancy must not disappear behind a single confidence score. Report scenario spread separately from any calibrated prediction interval. Yield and profit prediction remain deferred unless suitable targets, response models and independent evidence are obtained.

## 7. Candidate strategies and crop catalog

- Compare at least three eligible strategies including current practice. When fewer are supported, disclose the shortage; do not fabricate alternatives.
- Initial crop subset and demonstration locations are chosen by verified source coverage, parameter availability and contrasting agricultural systems. Broad crop coverage is incremental, not a release claim.
- Distinguish species, crop use and cultivar; a species profile does not validate all commercial seed varieties.
- Record annual/perennial status, crop family, season, stage lengths, planting window, Kc, root depth/development, depletion parameters, soil constraints and references needed by each enabled calculation.
- Support a declared strategy horizon. The first engine can compare next-season candidates using history; multi-season plans need their own sequence representation, calendars and carried-forward soil states.
- Run hard constraints before simulations. Separate unsupported choices from agronomically unsuitable choices.
- Priorities select the presentation or an explicitly disclosed multi-criteria method. They never change physical calculated quantities.

## 8. Data ingestion, alignment and integrity

1. Validate geometry, crop, calendar, management and requested output.
2. Resolve geographic and temporal coverage for each required product.
3. Fetch or reuse a matching versioned cache entry; retain the immutable original response and request.
4. Validate response schema, source identity, units, dates, geometry semantics and quality flags against the product contract.
5. Create a separate normalized dataset, recording conversions and spatial/temporal aggregation.
6. Join aligned daily forcings, soil properties and crop/management parameters.
7. Calculate indicators and simulations, perform physical checks and attach uncertainty/limitations.
8. Save immutable analysis and result snapshots; return JSON and a readable report.

Data-reading integrity remains strict: no silent value changes, missing-as-zero substitutions or acceptance of mismatched requests. However, coordinate checks must follow the provider's documented return semantics: a returned cell centre need not equal the requested field point. Distinguish source-declared missing observations from a structurally incomplete response.

Match time standards and interval definitions explicitly. Precipitation totals, average fluxes and instantaneous measurements require different aggregation. Document area weighting, leap days, crop-year boundaries, time zones, quality filtering and incomplete-season rules.

Cache keys include provider, product/version, variable, spatial support, period, time standard and processing version. Keep reference records distinct from model input records and from test-only corrupted fixtures.

## 9. Validation and error policy

### Separate error categories

| Category | Policy |
|---|---|
| Source integrity | Exact preservation and contract checks; fail corrupt or mismatched records |
| Floating-point calculations | Unit-aware absolute/relative tolerances justified by numerical precision and reference examples |
| Physical consistency | Check dimensions, water conservation, storage/flux limits and model applicability |
| Environmental accuracy | Compare aligned outputs with suitable independent reference observations |
| Agronomic validity | Review parameters, crop/region scope and interpretations with domain evidence |

Zero tolerance for source corruption is not zero physical uncertainty. Do not compare derived floating-point outputs with arbitrary exact equality or promise zero analytical error.

Report MAE, RMSE and signed bias for continuous outputs, with units, sample count and population. For categorical outputs report per-class confusion results and coverage where a defensible reference exists. Missing/unavailable results are counted and reported, not excluded invisibly to improve accuracy.

For seasonal or spatial estimates quantify uncertainty using an appropriate design. Sensitivity analysis and, when justified input distributions are available, Monte Carlo propagation can assess parameter uncertainty; account for correlated inputs. They do not by themselves validate the model or establish future confidence levels.

Set metric-specific acceptance thresholds after the pilot study and before evaluating the final holdout. Record the rationale and model limits. Do not adopt one universal percentage tolerance or reuse the Hebron site-ratio cutoffs as a nationwide scientific standard.

## 10. Sampling and independent evaluation

Sampling unit: a distinct source spatial support or well-defined field geometry plus crop season. Multiple points in the same coarse weather cell are not independent weather samples.

Create a reproducible sampling frame over U.S. agricultural locations. Stratify by agroclimate, crop/system, irrigation, soil and terrain as feasible. Include Alaska and Hawaii in coverage testing even when outputs there are partial. Ensure sampled crops are actually eligible for the chosen analysis.

Planning starting point: up to 100 distinct locations with up to 10 complete seasons each where compatible source periods allow. This is a pilot budget, not a statistically justified final sample size or 1,000 independent observations. Revise after measuring missingness, variance, spatial dependence and reference availability.

- Use a stored random seed, selection probabilities and inclusion/exclusion reasons.
- Keep sampling weights when reporting population summaries from disproportionate strata.
- Hold out whole spatial groups; also test later seasons to examine temporal generalization.
- Keep final holdouts untouched during parameter tuning. If using grouped cross-validation, design it around the spatial/temporal dependence and deployment question.
- Sources sharing underlying observations or models are not automatically independent validation evidence.
- Do not use CDL or GAEZ as both an engine input and unquestioned truth for evaluating that same inferred result.
- NASA-only checks establish reproducibility and cross-product agreement; field accuracy needs an appropriate external reference.

Each sample records sample ID, geometry/support IDs, state, stratum, season, crop/management provenance, dataset versions, QA, expected/reference output, assignment to evaluation groups and exclusion reasons.

## 11. System architecture and implementation

Retain Python + FastAPI as the backend foundation. Separate provider adapters, normalized models, scientific calculations, crop/rotation rules, orchestration, validation and explanation generation.

Pipeline:

Request -> geography/coverage -> validated source records -> normalized daily inputs -> indicators and physical models -> strategy comparison -> quality/uncertainty -> immutable result -> CLI/report/API -> web

Implement pure calculation functions independently of network and storage so reference and physical tests run offline. No generative AI is required to calculate or explain results; use deterministic templates tied to equations and evidence.

Extend the existing database through explicit migrations; do not overwrite historical Hebron analyses. Store source datasets independently and link analyses to the versions used, allowing safe reuse across runs. Add geometry/support references, product coverage, soil profiles, crop parameters, management scenarios, model runs and validation metadata as needed. Avoid embedding duplicate code listings in this specification; executable source files become the implementation authority.

### Analysis request

Include location or field geometry, country/scope, analysis type, crop-history provenance, candidate strategy IDs, calendar, irrigation and management assumptions, soil source/overrides, weather/scenario period and goal.

### Analysis response

Include analysis ID/status, supported outputs, coverage per dataset, source provenance, input states, model/parameter versions, per-strategy quantities and units, equation IDs, historical/scenario/predictive result type, uncertainty, assumptions, physical checks and limitations. Preserve entered/estimated/assumed/missing labels.

Keep existing versioned routes where compatible; version breaking request/response changes. API contract tests precede web integration. Sample mode is explicit and never passed off as a live fetch.

## 12. Delivery order and milestone gates

### Phase 1 — Data and scientific design

Select U.S. demonstration locations and a limited supported crop set. Verify NASA weather variables, soil inputs and agricultural references. Define target quantities, equations, units, model applicability and the canonical analysis contract. Download versioned fixtures, including coverage-failure examples.

Gate: at least one reproducible U.S. forcing record, one usable crop/soil configuration and independently checked reference calculations. Identify what remains missing before expanding.

### Phase 2 — Analysis and outcome-estimation engine

Implement ingestion, provenance, ET0, crop demand, eligible water-balance scenarios, historical indicators and at least three strategy comparisons. Add rotation evidence and physical checks. Produce JSON and a human-readable report without needing the web.

Gate: reference calculations and physical tests pass; U.S. sample runs are reproducible; missing-data and unsupported-region paths work; no unsupported predictive claims appear.

### Phase 3 — Evaluation and prediction eligibility

Run stratified pilot sampling, independent reference comparisons and grouped/spatiotemporal evaluation. Document bias, errors, missingness and limitations. Tune only on development groups. Enable a predictive output only when its predefined validation gate passes; otherwise deliver labelled historical scenario estimation.

Gate: a reviewable validation report, known performance limits and a frozen demonstration dataset. No worldwide or all-crop accuracy claim.

### Phase 4 — U.S. web experience

Adapt the existing prototype after the analysis contract stabilizes. Display all 50 states; allow point/field selection, crop history, season and goals; review inputs; run analysis; compare strategies; inspect equations and evidence; print/export results. Handle loading, partial coverage, unsupported location, provider/data error and offline report viewing.

Gate: complete backend-to-web demonstration on desktop and mobile; results match the saved engine output. Backend owns all scientific calculations. Existing UI code may be reused where compatible.

### Phase 5 — Optional Palestine extension

Only start if Phases 1–4 and submission materials are complete and time remains. Keep U.S. default scope and add an explicit Palestine option with verified boundaries and product coverage. Enable applicable global datasets; never display U.S.-only layers as Palestinian evidence. Soil/history may need user input or remain unavailable.

Reuse equations only within their applicability and with valid local parameters/calendars. Existing Hebron fixtures can serve regression tests, not automatic scientific validation. Deliver partial climate analysis when local evidence cannot support a crop/water conclusion. If unfinished, mark Palestine as planned and keep it out of the working demo path.

## 13. Acceptance criteria

1. Every enabled numerical output has a documented equation, units, parameter provenance and applicability.
2. Source records are preserved; invalid data fails explicitly and missing data remains missing.
3. Daily ET0/crop-demand results reproduce independent published or independently calculated reference cases within justified numerical tolerances.
4. Water-balance runs satisfy explicit conservation and storage tests, including irrigation and dry/wet boundary cases.
5. Unsupported snow/frozen-soil or other model conditions produce a clear limitation or unavailable output.
6. The API accepts U.S. locations throughout all 50 states and returns product-specific coverage or a clear applicability status; outside-scope locations are rejected.
7. At least three eligible strategies including current practice are demonstrated, with the five challenge-required explanation elements.
8. Outcome estimates clearly distinguish historical analysis, conditional simulation and validated prediction.
9. Sampling/evaluation records expose group splits, references, errors and unavailable cases; no accuracy number is claimed without evidence.
10. Changes create a new immutable analysis; historic Hebron results remain unchanged.
11. The web map displays all 50 states, and the interface shows the backend evidence and limitations consistently.
12. Changing farmer priorities does not change physical outputs; any ranking method is explicit.
13. Demo, reference data and live retrieval are visibly distinguished.
14. Palestine is either a tested optional extension using covering sources or explicitly planned.

## 14. Submission and presentation requirements

The supplied event slide is a submission-planning reference. Prepare the Project page before the event deadline; confirm the exact deadline from the event organizers/site rather than infer a time from the slide.

- Public project link opens without login or permission requests.
- Mandatory demo: the supplied slide states a video up to 30 seconds or a presentation up to seven slides including the title slide. Recheck organizer requirements before final export.
- Project page and attachments in English. A video in another language includes English translation/subtitles.
- Use relevant NASA/partner data and cite every dataset, model reference, library and reused asset; disclose tool/AI use as required by submission guidance.
- Observe the event's original-work and build-period requirements. Document provenance of pre-existing material honestly; this document does not certify competition eligibility.
- State implemented, simulated, validated and planned features separately. Keep the U.S. scientific demonstration and its evidence ahead of optional geographic expansion.

Demo narrative: choose a U.S. agricultural location, show source coverage, enter or confirm soil/history/management, compare current practice with alternatives, reveal the water-demand/balance equations and evidence, explain uncertainty, and export the result.

## 15. Migration checklist from v3.2

| Existing element | Required change |
|---|---|
| Hebron-only input validator | U.S. boundary and product/applicability checks |
| 0.1-degree coordinates everywhere | Analysis geometry separated from public-location privacy |
| October–May and 2026/27 literals | Crop/location-specific calendar and explicit scenario years |
| Wheat/lentil/vetch fixed plans | Versioned U.S. crop catalog and eligible strategy builder |
| Fixed Hebron station JSON | Versioned, spatially/temporally matched reference records |
| Seasonal rain vs fixed crop need label | ET0, stage-specific demand and eligible daily water-balance method |
| Draft Hebron rules | Region/crop-specific rules and parameter review |
| Hebron expected numerical outputs | Retained regression fixtures plus new independent U.S. cases |
| Single rainfall dataset assumptions | Product-specific adapters, alignment, coverage and provenance |
| UI-first build order | Engine and validation first; web integration afterward |
| Global ambition / Palestine pilot | U.S. release; Palestine only after core delivery if time remains |

Do not remove useful tests merely because their old geography is outside the new default. Classify regression tests separately from U.S. release acceptance. This document does not claim the migration has been implemented.

## 16. Source references

- Challenge resources: https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/?tab=resources
- NASA POWER Daily API: https://power.larc.nasa.gov/docs/services/api/temporal/daily/
- NASA POWER methodology: https://power.larc.nasa.gov/docs/methodology/
- FAO-56 reference ET: https://www.fao.org/4/x0490e/x0490e08.htm
- FAO-56 crop coefficient: https://www.fao.org/4/X0490E/x0490e0b.htm
- FAO-56 full manual, USDA-hosted copy: https://www.wcc.nrcs.usda.gov/ftpref/wntsc/waterMgt/irrigation/fao56.pdf
- GPM IMERG: https://gpm.nasa.gov/data/imerg
- SMAP L4: https://nsidc.org/data/spl4smgp/versions/8
- USDA crop-layer releases, including Hawaii: https://www.nass.usda.gov/Research_and_Science/Cropland/Release/index.php
- Web Soil Survey: https://websoilsurvey.nrcs.usda.gov/app/HomePage.htm
- PRISM dataset descriptions: https://ftp.prism.oregonstate.edu/PRISM_datasets.pdf
- FAO GAEZ: https://www.fao.org/gaez/en
- NIST uncertainty propagation: https://www.nist.gov/publications/concepts-principles-and-methods-assessment-measurement-uncertainty

Source links identify starting references, not completed integrations. Record exact dataset identifiers, retrieval dates, licenses, parameter tables and reference calculation cases in the implementation evidence register.
