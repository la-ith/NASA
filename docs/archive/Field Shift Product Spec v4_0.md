# Field Shift — Final Implementation Specification

Version 4.0 | 14 November 2026 | NASA Space Apps Challenge 2026

**Planning baseline approved through the project conversation. Implementation and scientific validation are separate milestones.**

Build order: U.S. data and mathematical engine -> validation -> U.S. web and interactive map -> grounded agricultural chatbot -> optional Palestine extension.

This document is the implementation authority for the new release. Sections 1–16 define the scientific and delivery baseline; sections 17–25 specify the map, ingestion contracts, chatbot, engineering interfaces and execution checklist. Read them together.

## 1. Status and decisions

This is the current product and implementation plan. It supersedes v3.3 and v3.2. Preserve earlier files as historical references; their code listings, Hebron measurements and expected results are not validation evidence for the U.S. system.

User-confirmed decisions:

- Primary geography: the United States, all 50 states including Alaska and Hawaii.
- Build and validate the data-analysis and outcome-estimation system first. Build or adapt the web interface after the backend milestone passes.
- Use relevant NASA environmental data and available U.S. agricultural reference data. The 24 challenge resources are a source catalog, not a requirement to integrate every source.
- Ground numerical analysis in documented physical equations and explicit mathematical methods.
- Use MapLibre GL JS for the interactive map, with separately licensed basemaps and scientific layers.
- Include a grounded AI agricultural chatbot after the U.S. web milestone. It explains analysis and supports crop-care questions with evidence; scientific calculations remain backend tools.
- Palestine is an optional extension only after the U.S. analysis, web and chatbot milestones and submission preparation, if time remains. Use only products that cover the selected Palestinian location.
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

Implement pure calculation functions independently of network and storage so reference and physical tests run offline. Deterministic explanations are part of every analysis. The approved generative chatbot is a separate grounded interface to results, references and authorized scenario tools; it never replaces physical calculations.

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

### Phase 5 — Grounded agricultural chatbot

Implement the chatbot described in section 20 after the U.S. web flow works. Connect it to approved agronomic references, the selected field and immutable analysis snapshots. Add evidence citations, tool permissions, unsupported-question handling, stale-data handling and model/service failure states.

Gate: factual/tool-grounding evaluation passes, quantitative claims match engine output, no state changes occur without confirmation, and users can inspect sources. The deterministic analysis and map remain usable when chat is unavailable.

### Phase 6 — Optional Palestine extension

Only start if Phases 1–5 and submission materials are complete and time remains. Keep U.S. default scope and add an explicit Palestine option with verified boundaries and product coverage. Enable applicable global datasets; never display U.S.-only layers as Palestinian evidence. Soil/history may need user input or remain unavailable.

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
15. Map interactions, legends, units, time periods and returned pixel/field values remain consistent with the selected analysis and dataset.
16. Chat factual answers cite retrieved evidence; numerical analysis claims match tool results, and insufficient/current-data limitations are explicit.
17. Chat cannot override source data, scientific rules, access controls or persisted farmer inputs through generated text.

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

## 17. Exact challenge catalog: 24 entries

Keep the challenge's grouped entries intact when counting. This is a catalog, not a 24-adapter launch requirement. Coverage below is a routing category; a verified product footprint and dates govern actual availability.

| # | Resource entry | Geographic category | Initial treatment |
|---|---|---|---|
| 1 | SMAP | Shared internationally, product-dependent land coverage | Next: moisture context |
| 2 | GPM / IMERG | Shared internationally | Next: precipitation adapter |
| 3 | Landsat and MODIS/VIIRS | Shared internationally | One selected vegetation product first |
| 4 | NASA POWER | Shared internationally | Core weather adapter |
| 5 | SRTM | Shared, limited latitude range | Optional terrain; coverage fallback needed in Alaska |
| 6 | ECOSTRESS | Shared, limited orbital/observation coverage | Optional ET/surface temperature |
| 7 | USDA Ag Data Commons | Dataset-specific repository | Evidence discovery, not a uniform map layer |
| 8 | Web Soil Survey | U.S. survey coverage | Soil access; overlaps underlying SSURGO information |
| 9 | USDA CDL / CropScape | U.S. crop products | Crop classification; check separate Hawaii product |
| 10 | PRISM | Primarily contiguous U.S. products | Climate comparison where covered |
| 11 | SSURGO / STATSGO2 | U.S., survey/product-dependent | Core soil properties where available |
| 12 | NAIP | U.S., acquisition-dependent | Optional aerial imagery |
| 13 | NLCD | U.S., product/version-dependent | Optional land-cover context |
| 14 | NLDAS / GLDAS | Mixed: regional / broadly global land products | Verify each separately |
| 15 | FAO GAEZ | Shared internationally | Optional crop suitability context |
| 16 | CoCoRaHS | Regional North American station network | Reference observations where present |
| 17 | USGS NWIS | U.S. station network | Optional hydrologic context |
| 18 | USDA AMS Market News | U.S. market reporting | Later; no profit forecasts at launch |
| 19 | USDA NASS QuickStats | U.S. agricultural statistics | Aggregate context, not field truth |
| 20 | OpenET | U.S. product-dependent coverage | Optional ET comparison |
| 21 | USFS LANDFIRE | U.S. product-dependent coverage | Optional ecosystem context |
| 22 | GEDI | Shared internationally, orbital footprint sampling | Optional tree/landscape context |
| 23 | Copernicus Sentinel-2 | Shared internationally | Optional vegetation imagery; ESA source |
| 24 | ERA5 | Global | Optional climate context; ECMWF/Copernicus source |

Catalog grouping: 11 U.S.-focused entries, 10 internationally shared entries, 3 mixed/regional/repository entries. Neither category guarantees a valid observation for every U.S. field. Preserve current metadata rather than freezing older challenge descriptions of resolution or coverage.

## 18. Operational ingestion specification

### 18.1 Access routes

- POWER: direct daily API calls through the backend; confirm the parameter catalog and returned units for the requested community/time standard.
- Earthdata products: use the collection/granule search and product-supported download/subsetting route. Python `earthaccess` is an implementation candidate for authentication, search and retrieval.
- AppEEARS: use point/area extraction with quality layers only for products listed as available by that service. Requests can be asynchronous.
- NASA GIBS: optional visualization tiles, not the numerical source for physical calculations.
- USDA and other references: independent adapters for their supported query/download mechanisms. Earthdata credentials do not grant access to every non-NASA source.

Keep Earthdata/service credentials server-side, outside source control and logs. Anonymous public browsing of the project must not require each judge to log into Earthdata. Use permitted server-side cached records and labelled sample mode for the demo. Provider rate limits, access restrictions and reuse licenses still apply.

### 18.2 Initial weather mapping

| Canonical quantity | POWER parameter candidate | Target analysis unit | Required handling |
|---|---|---|---|
| Daily precipitation | PRECTOTCORR | mm per daily interval | Confirm rate/interval semantics and fill marker |
| Daily air temperature extrema | T2M_MIN, T2M_MAX | degrees Celsius | Preserve extrema; check Tmin <= Tmax |
| Daily mean air temperature | T2M or a documented FAO mean-temperature method | degrees Celsius | Record which method supplies T |
| Humidity | RH2M or a verified vapour-pressure/dew-point route | %, then derived kPa where needed | Use the applicable FAO derivation; quantify limitations of mean RH |
| Wind at 2 m | WS2M | m/s | Verify height; convert alternative heights with documented method |
| Incoming shortwave radiation | ALLSKY_SFC_SW_DWN | MJ/m²/day | Read response units; convert only in normalized data, then derive Rn |
| Pressure/elevation | Verified PS and/or documented elevation metadata | kPa / m | Define the FAO pressure route and terrain representativeness |

These are candidate identifiers to verify, not a statement that all products or response units have been tested. Store original metadata and unit conversion tests. Do not run physical ET0 with whichever variables happen to arrive if essential inputs are missing.

### 18.3 Adapter interface

Each adapter implements:

- `describe_product()`: version, license, variables, units, temporal semantics, grid/footprint, support limits.
- `check_coverage(geometry, interval, variables)`: supported/partial/unsupported/unknown plus reasons.
- `fetch(request)`: bounded attempts, timeouts, request manifest and original artifacts.
- `validate(raw, request)`: contract checks, missingness and QA without altering the original.
- `normalize(validated)`: typed values with explicit transformations and native support IDs.

Do not synchronously download national high-resolution archives when a user opens a map. Precompute reusable overviews, fetch spatial/time subsets on demand, and queue expensive jobs. Cache by source/version/support/time and invalidate derived results when the model or input versions change.

Use one retry for transient failures within the provider's limits; respect Retry-After. Do not retry a malformed request automatically. A provider timeout, integrity failure and absence of coverage have distinct error codes.

### 18.4 Dataset manifest

Required fields: dataset ID, provider, collection/product ID, version, variable, original units, normalized units, time standard, interval, requested geometry, returned supports, CRS, nominal resolution, quality mask/version, retrieval UTC, original artifact URI, content hash, adapter version, transformations and license/reference.

Original records are immutable. Content hashing checks local integrity, not scientific validity. An analysis references manifests and normalized artifacts rather than copying entire archives into a JSON response.

## 19. Interactive map and web specification

### 19.1 Map technology

Use MapLibre GL JS as the rendering library. It is separate from the basemap, imagery provider and analysis data. Select a production-permitted basemap with required attribution; a free library does not imply unlimited free tiles, imagery, hosting or compute. Never treat a public demonstration tile server as an unrestricted production service.

Use a compatible raster/vector tile service for scientific layers. Store appropriate derived rasters as Cloud Optimized GeoTIFFs; a server-side tile/query component exposes the needed views. Do not assume MapLibre directly reads every scientific COG, HDF or NetCDF format.

For the first delivery keep the existing frontend approach if practical; no framework rewrite is required. Use 2D mapping first. Terrain/3D is optional and cannot delay the core analysis, map or chat flow.

### 19.2 Map layout and interactions

- Opening view: United States with labelled shortcuts to contiguous states, Alaska and Hawaii.
- Location: search, coordinate entry, click point or draw field polygon. Typed input works if tiles fail.
- Field selection: show area, state, boundary validity and available-source summary. Drawing area is for the field geometry, not an automatic ownership/parcel assertion.
- Controls: layer selector, period/season selector, crop/strategy selector, opacity control and legend. A time slider is enabled only for genuinely time-indexed data.
- Selection panel: crop history, planting/harvest dates, soil input/source, irrigation management, goal and assumptions.
- Result panel: current practice and at least two eligible alternatives, with numerical outputs, benefits, concerns, sources and missing information.
- Evidence panel: equations, units, parameter sources, provenance, QA and uncertainty.
- Chat drawer: conversations refer to the visibly selected field and analysis; changing fields does not silently reuse old context.
- Report: printable comparison, source acknowledgements, result type, dates, model version and limitations.

### 19.3 Layers and semantics

| Layer | Quantity/units | Interaction | Availability rule |
|---|---|---|---|
| Precipitation | Daily/period total, mm | Select date/interval | Valid precipitation source |
| Air temperature | Defined daily/period statistic, degrees Celsius | Select statistic/interval | Matching weather data |
| Soil moisture | Product-defined volumetric fraction or other declared unit/depth | Select depth/date | Valid product and QA; never mix depths silently |
| Crop classification | Category/year | Select year and inspect class | Covering CDL or other approved layer |
| Soil properties | Chosen property/unit/map support | Select texture, water capacity or other supported property | Covering survey and explicit aggregation |
| Vegetation | NDVI/EVI, dimensionless | Select valid composite/date | QA-filtered imagery |
| ET0 | mm/day or declared period total | Select interval | Complete ET0 calculation |
| Crop demand | ETc_standard, mm | Select crop, calendar and interval | Crop profile and ET0 |
| Water deficit/stress | Defined model output and unit | Select strategy/scenario | Eligible balance simulation and necessary inputs |
| Strategy difference | Same output A minus B, same unit | Choose compatible strategies | Same forcing/support/period or disclosed comparison method |
| Data quality | Coverage, missingness or review state | Inspect reasons | Present for every analysis layer |

Raster spatial variation must come from spatially resolved inputs/model runs. A calculation for one field does not authorize a national deficit heatmap. Initially shade the analyzed field with its summary and display source rasters separately. Expand calculated surfaces only as covered cells are computed and validated.

Clicking a raster queries the scientific value from the corresponding dataset/model artifact; do not infer numeric values from rendered RGB colors. A field summary is labelled with its aggregation method, valid-area fraction and native supports. Categorical classes are never interpolated as continuous numbers.

### 19.4 State and recomputation

- Changing visible layer, opacity, map position or equivalent display units does not rerun the scientific model.
- Changing field, crop, calendar, soil/management inputs or weather scenario creates a new analysis. Cache reuse is allowed when inputs match.
- Changing comparison goals never changes physical quantities; persist a new comparison snapshot when narrative/ranking changes.
- Every displayed layer binds to a dataset/model artifact ID and, for derived layers, analysis/strategy ID. Show period, units, source and resolution.
- On new selection, show loading/stale status and prevent an older response from replacing a newer request.
- Unsupported coverage appears as masked/hatched space, not zero or a favorable color. Distinguish outside coverage, cloud-masked, missing period, provider failure and unsupported model conditions.
- Use consistent color scales for comparable strategies; show scale changes explicitly. Do not use smoothing to imply precision.
- Show a legend, text alternative and table for scientific quantities. Keyboard/focus and mobile controls remain usable.

## 20. Grounded agricultural AI assistant

### 20.1 Purpose and scope

The approved chatbot helps a farmer understand their crop, the selected field, analysis outputs and crop-care evidence. It answers in plain language, cites evidence and asks for missing decision-relevant details.

Core questions: explain a map value, explain differences between crop strategies, interpret water-demand estimates, discuss stage-specific care, identify information needed to assess symptoms and run an explicitly requested what-if simulation.

An initial symptom conversation supports observation and next steps; image-based diagnosis is not a launch capability. Exact pesticide dosing, disease confirmation and guaranteed treatment outcomes are not outputs of the environmental analysis engine.

### 20.2 Grounding architecture

Chat message -> field/analysis context resolver -> retrieval and read-only tools -> evidence package -> language model -> response validator -> cited answer

Grounding sources:

1. Immutable engine outputs: quantities, units, assumptions, quality and equation IDs.
2. Selected field/crop/calendar and user-confirmed management history.
3. Curated official agronomic references, such as FAO and applicable U.S. extension guidance, licensed for the intended retrieval/use.

Documents carry title, publisher, URL/document ID, publication/review date, region, crop scope, passage identifiers and ingestion version. A broad crop-care reference is not automatically a local management prescription. Do not feed an unrestricted web search directly into authoritative recommendations.

Use lexical/structured retrieval for a small initial corpus; add embeddings/vector storage only if retrieval quality justifies it. AI provider/model is configuration selected during implementation after checking tool support, privacy, latency and budget. Never embed API credentials in browser code.

### 20.3 Authorized tools

| Tool | Permission and behavior |
|---|---|
| Read selected field | Read-only; session/access scoped |
| Read selected analysis | Read-only immutable snapshot |
| Read coverage/provenance | Read-only; current selection |
| Search approved references | Return cited passages with applicable scope |
| Explain metric | Return equation and backend values, not LLM arithmetic |
| Run what-if scenario | User-requested calculation; creates a separate snapshot with assumptions, never overwrites the original |
| Propose field/history change | Show exact proposed changes; persist only after explicit user confirmation |

Chat has no direct raw-dataset write, rule-edit, unrestricted database, shell, external messaging or irrigation-control tool. Source passages and farmer messages are untrusted content, not instructions capable of changing tool permissions.

### 20.4 Answer contract

Return concise answer text plus structured evidence: claim-to-source links, analysis/strategy ID for numerical claims, relevant dates, assumptions and missing inputs, and any proposed action needing confirmation.

- Numerical scientific claims come from tools and retain their units/period. Validate values against the cited snapshot rather than trusting generated text.
- Distinguish an observation, a simulated scenario and general agronomic guidance.
- If evidence is insufficient or contradictory, explain the specific gap. Do not fill it with an invented fact or citation.
- Do not say 'irrigate today' using historical climate alone. Current management, growth stage, water state and suitable current/forecast information are required for an operational assessment; until integrated, explain the limitation.
- On ambiguous symptoms ask about crop, stage, timing, distribution, irrigation and relevant observations; avoid a confident disease diagnosis from environmental data.
- When a scenario changes assumptions, show the changes and the result type. A difference in simulated outputs is not a proven causal benefit in the real field.
- If the model service fails, display a retry option and deterministic engine explanations. Keep the map and report working.

### 20.5 Privacy, limits and evaluation

Send only context needed for the question. Do not send exact geometry to an external model unless needed and covered by the product's disclosed data handling. Enforce session ownership on fields, reports, chats and tools. Apply request/token limits and configurable budget caps. Avoid exact coordinates or full sensitive conversations in diagnostic logs.

Create an evidence-reviewed evaluation set covering supported questions, incorrect premises, missing/current-data cases, conflicting references, stale analysis, field switching, prompt injection in retrieved documents, fabricated citations, numerical mismatches, unauthorized mutation and tool failure. Use deterministic checks where possible and agronomic review for answer validity; another LLM's preference alone is not validation.

For release, the fixed critical suite must show no unauthorized mutations, invented tool outputs or accepted numeric mismatches. Report citation support and answer-quality results and remaining gaps; passing the suite is not proof of zero future errors. Keep analysis integrity tests separate from chat fluency checks.

## 21. Engineering contracts and storage

### 21.1 Proposed module structure

```text
backend/app/
  api/                  # coverage, crops, analyses, jobs, layers, reports, chat
  domain/               # typed crop, soil, management, strategy and result models
  adapters/             # POWER, Earthdata products, USDA/reference providers
  science/              # units, FAO56, crop stages, balance, indicators, uncertainty
  geo/                  # boundaries, native supports, aggregation and queries
  services/             # orchestration, caching, provenance, explanations
  chat/                 # context, retrieval, tool permissions, response validation
  storage/              # migrations, immutable manifests, analysis snapshots
frontend/
  ...                   # adapt existing app; map, forms, comparison, evidence, chat
data/
  fixtures/             # small versioned U.S. samples and regression fixtures
  catalogs/             # product registry, crop profiles, approved reference metadata
docs/
  validation/           # sample manifest, thresholds, results and limitations
  data-sources.md
  equation-register.md
  decision-log.md
```

This is a target separation, not an instruction to relocate functioning modules before needed. Keep executable calculations in source files, not copied into Markdown. Maintain dependency pins after compatibility checks.

### 21.2 Versioned API target

Use `/api/v2` for the new incompatible contract and retain `/api/v1` for existing regression fixtures until explicitly retired.

| Method/route | Purpose |
|---|---|
| GET /api/v2/health | Service readiness without leaking secrets |
| POST /api/v2/coverage | Product/output availability for geometry and interval |
| GET /api/v2/crops | Crop profiles and eligible calculation capabilities |
| POST /api/v2/analyses | Validate request, create analysis/job and return result or job handle |
| GET /api/v2/jobs/{id} | Queued/running/succeeded/failed/cancelled state and stage |
| GET /api/v2/analyses/{id} | Retrieve authorized immutable result |
| GET /api/v2/analyses/{id}/report | Readable/printable report |
| GET /api/v2/analyses/{id}/layers | Derived-layer manifest |
| POST /api/v2/layer-values | Query point/field values from an authorized layer |
| GET /api/v2/tiles/{layer_id}/{z}/{x}/{y} | Display tiles where the chosen tile service uses this route |
| POST /api/v2/chat/sessions | Create field/analysis-scoped chat session |
| POST /api/v2/chat/sessions/{id}/messages | Grounded answer/tool execution |

Pin request/response schemas before web integration. Return 202 with a job handle for expensive work; do not leave the browser on an indefinite synchronous request. Error envelopes include code, stage, readable message, retryability and optional field errors. Job operational records may be mutable; successful scientific snapshots remain immutable. Store failed-job diagnostics without claiming they are completed analyses.

Analysis request minimum: schema version, geometry/point with CRS, candidate calendar, history and provenance, at least three requested/eligible strategies or an explicit builder request, irrigation/soil input states, historical/scenario mode, weather period and goal. Missing mandatory inputs can produce field errors or limited capabilities, not fabricated defaults.

Result statuses: `complete`, `partial`, `unsupported`; job errors have their own status. `complete` means all requested supported outputs were computed, not high scientific confidence. All responses identify capabilities and limitations.

### 21.3 Layer manifest

Required fields: layer ID, title, quantity, unit, result type, source/product/version, analysis/strategy IDs if derived, interval/time dimension, native CRS/support/resolution, bounds/coverage mask, aggregation, no-data reason codes, legend thresholds/palette, display range, tile endpoint, value-query contract and attribution.

Legend classifications must reference versioned physical thresholds or an explicit display method. Quantile colors describe distribution, not agronomic suitability. Display-unit conversion preserves source units and avoids recalculating scientific results.

### 21.4 Persistence and access

Retain SQLite for the initial single-instance prototype where suitable. Store large raster/time-series artifacts in filesystem/object storage with manifests and checksums, not as huge response blobs. Introduce PostgreSQL/PostGIS when concurrent spatial querying and deployment require it; this is not a prerequisite to validate the scientific engine.

Store fields and access scopes, crop-history provenance, dataset manifests/artifacts, crop/soil/model versions, strategy snapshots, model runs, result metrics, layer manifests, validation references, operational jobs and scoped chat messages/citations/tool events. Separate source observation provenance from user overrides and model estimates.

For a no-account demo, use unguessable session-bound access tokens/cookies, not possession of a short public analysis ID as authorization. Public sample reports are explicit and omit sensitive geometry. Restrict CORS, validate polygon size and query intervals, bound downloads/jobs and redact secrets from logs.

## 22. Scientific reference cases and test plan

The approximately 60 cases discussed earlier are a planning estimate, not a quality gate by count. Organize tests by requirements and failure risk.

| Group | Required cases |
|---|---|
| Geography | All 50 states represented in boundary tests; Alaska antimeridian; Hawaii; outside U.S.; ocean/invalid geometry; product-specific absence |
| Source integrity | Missing/extra dates, wrong units/variables, fill values, impossible values, QA, schema/version change and returned support semantics |
| FAO56 | Independent reference cases; radiation/vapour-pressure/height conversions; latitude/date/elevation; missing inputs; no premature rounding |
| Water balance | Dry/wet days, rain-fed vs supplied irrigation, initial storage, drainage/runoff, layered soil, growing roots if enabled, closure and unsupported snow/freeze |
| Crop/rotation | Unsupported crop, crop-stage dates, season boundaries, unknown history, source conflicts, reviewed vs draft rules and three eligible strategies |
| Historical estimation | Matching forcing across candidates, incomplete seasons, baseline overlap, no future leakage and honest distribution labels |
| Validation | Spatial/time group isolation, frozen holdout, weighted summaries where needed, sample attrition and metric units |
| Storage/API | Immutable historical results, access isolation, schema compatibility, cache invalidation and asynchronous failure/retry |
| Map | Layer/value agreement, date/unit/legend consistency, stale-response ordering, missing masks, field vs cell resolution and mobile accessibility |
| Chat | Grounding, citation support, numerical identity, incomplete/current-data handling, scoped tools, confirmation and model/provider failure |

Reference cases include actual inputs, expected outputs, reference provenance, derivation independent of the implementation, method-specific numeric tolerances and reviewer. Never generate expected values from the same function being tested and call that an independent check.

Example unit sanity check, not a field validation claim: theta_FC=0.30, theta_WP=0.15, Zr=1 m gives TAW=150 mm; p=0.5 gives RAW=75 mm. Kc=1.1 and ET0=4 mm/day gives standard ETc=4.4 mm/day. These synthetic values test units/arithmetic only.

## 23. Build backlog, gates and readiness

| Order | Work package | Reviewable artifact | Completion gate |
|---|---|---|---|
| 1 | Inventory existing prototype and preserve regression fixtures | Migration map and baseline test report | Existing/new scope clearly separated |
| 2 | Verify product access and U.S. boundary | Product registry, coverage checks, real U.S. fixtures | Data can be reproduced; no secret in repository |
| 3 | Freeze crop/soil/calendar subset and equation methods | Equation/parameter registers and independent cases | Inputs and unsupported cases are explicit |
| 4 | Implement ET0, demand and eligible balance | CLI/API report with three strategies | Numerical and physical tests pass |
| 5 | Evaluate sampled locations/seasons | Validation report and frozen holdout | Metrics and limitations support enabled claims |
| 6 | Implement layer artifacts and value queries | Layer manifest and matching numeric queries | Rendering inputs agree with scientific outputs |
| 7 | Adapt web and MapLibre interface | Complete U.S. map-to-comparison-to-report flow | Desktop/mobile and no-data/error states work |
| 8 | Add grounded chatbot | Cited crop-care and analysis conversations | Critical grounding/access tests pass |
| 9 | Prepare competition submission | Public link, English materials, references and demo | Anonymous review path works |
| 10 | Optional Palestine | Separate tested coverage mode | Core delivery complete and time remains |

Use role labels (data, science/agronomy, backend, geo/web, AI/retrieval, integration/submission); assign actual people in the decision log without inventing owners. Parallel work is possible on contracts and approved fixtures, but web/AI cannot define different scientific calculations from the engine.

### Launch minimum and stretch boundary

Required product path: real U.S. NASA data -> reproducible scientific outputs for a documented crop subset -> at least three strategy comparison -> all-state navigable map with honest coverage -> grounded chat -> readable report and references.

Required geography is all-state selection/coverage checking; this does not certify every crop/model in every state. A valid partial analysis is acceptable where evidence or model applicability is incomplete, and such limits are visible in the demo and submission.

Stretch: additional datasets/crops, independently validated future-target prediction, multi-season simulation, national derived rasters, advanced 3D and Palestine. If time is short, reduce optional data/model breadth first; do not fabricate results or hide critical gaps to meet the feature list. The mandatory demo path and honest implementation status remain explicit.

### First implementation run

1. Read this file, inventory actual modules and run the existing backend tests without altering historical fixtures.
2. Create the product/equation registers and one versioned U.S. weather fixture.
3. Implement `/api/v2/coverage` and pure ET0 functions against independent reference cases.
4. Add a sourced crop profile and demand calculation, then the applicable soil-water balance.
5. Produce the first machine-readable U.S. comparison before integrating map or chat.

Do not block this sequence on a final model vendor, global crop catalog or integrating all 24 entries.

## 24. Remaining implementation decisions and defaults

These items do not change the confirmed product scope. Resolve through product metadata, tests and the evidence register; ask for user input only when a material scope, cost or external commitment requires it.

| Item | Working default / resolution |
|---|---|
| U.S. demo sites and crops | Select by verified access and agronomic parameter completeness; record chosen sites/crops before model development |
| Web language | Complete English interface and submission first; architecture allows localization; no partial language selector |
| Chat language | English required; other languages only after terminology/grounding checks |
| Scientific date range | Product-overlap-aware, crop-specific calendars; record requested/actual range per analysis |
| Forecast target/horizon | No default weather/yield forecast claim; historical replay until an explicit validated target is enabled |
| Basemap provider | Choose permitted development tier and attribution; document usage limits before deployment |
| AI model/provider | Backend configuration; verify current API, cost and privacy before integration; mock tools are clearly labelled in development |
| Production storage/queue | Start small; select persistent job/storage service when deployment needs are known |
| Error thresholds | Set per metric after pilot and before holdout; document justification rather than invent a universal percent |
| Agronomic review | Record reviewer/status for each profile/rule; unrevised content is illustrative and labelled |
| Competition deadline | Use the organizer's exact local/UTC deadline; do not infer it from the screenshot |

## 25. Map, ingestion and AI reference register

- MapLibre documentation: https://maplibre.org/maplibre-gl-js/docs/
- MapLibre project/license: https://github.com/maplibre/maplibre-gl-js
- NASA GIBS access: https://nasa-gibs.github.io/gibs-api-docs/access-basics/
- Earthdata Search: https://search.earthdata.nasa.gov/
- NSIDC earthaccess guidance: https://nsidc.org/data/user-resources/help-center/downloading-nsidc-daac-earthdata-cloud-data-using-earthaccess
- AppEEARS: https://appeears.earthdatacloud.nasa.gov/
- NASA COG standard: https://www.earthdata.nasa.gov/s3fs-public/2024-05/ESDS-RFC-049%20Cloud%20Optimized%20GeoTIFF%20V1.pdf

The supplied event-slide image is a planning reference for section 14. Preserve its interpretation separately from confirmed online submission rules. The selected AI provider's official documentation, retrieved agronomic documents, source-specific licenses and exact product identifiers are added to the evidence register during implementation.
