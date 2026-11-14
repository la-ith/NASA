# Field Shift — Product and System Specification

Version 3.1 | NASA Space Apps Challenge 2026 | Proposed build plan

**Changes in 3.1:** Section 14 now holds proposed answers instead of open questions. New sections 16–19 add the data dictionary, indicator definitions, the draft rule set, and an implemented/simulated/planned table. Everything added in 3.1 is a team proposal until the named owner confirms it.

**Status:** This specification describes intended behavior, not completed features. Items marked MVP are the recommended hackathon build. Other items are later releases.

## 1. Vision

Field Shift helps a farmer compare a few crop rotation options for one field using historical climate context and transparent, locally reviewed agricultural rules.

**Promise:** Compare options, see why they differ, understand the evidence and uncertainty, and make an informed decision with local expertise.

It is decision support—not a yield guarantee, weather forecast, or replacement for an agronomist.

### First user and demo case

Primary user: a smallholder farmer or advisor planning the next season for a rain-fed field.

Demo scenario: a representative field near Hebron with repeated wheat in its recent history. Compare the next-season wheat option with up to two next-season alternatives, such as lentil and vetch, only if a local agricultural reviewer confirms the rules. Each option is evaluated against the same recorded crop history; the demo remains illustrative until data and agronomy are verified.

### What success looks like

A user can enter a field and crop history, see the coverage and quality of the climate data, compare up to three plans, understand each trade-off and limitation, and save or print the comparison.

## 2. Product principles

1. Evidence first: every indicator and agricultural rule has a definition, source, units, and applicable region.
2. Honest uncertainty: missing data is never zero; historical conditions are never called a forecast.
3. Rules calculate; explanations explain. AI cannot change results or invent agricultural facts.
4. Keep the first release narrow: one pilot area, a few crops, one verified climate source.
5. The farmer chooses. The app displays trade-offs rather than silently deciding.
6. Mobile first and low bandwidth friendly.
7. A complete, credible workflow is better than many unfinished features.

## 3. Scope

### MVP — build for the hackathon

- Responsive web application that can be installed as a PWA.
- One pilot location and one sample field.
- Field details: approximate location, area, irrigation, optional known soil type.
- Recent crop history with an explicit unknown option.
- One verified source for historical rainfall, proposed NASA POWER.
- Data validation, units, source and date range displayed to users.
- Small, cited crop/rotation rule set reviewed by an agricultural domain reviewer.
- Current practice and up to two alternatives.
- Check hard constraints before comparing plans.
- Compare supported criteria such as water fit, rotation/soil benefit, and risk.
- Evidence-linked explanations and visible limitations.
- Print-friendly comparison report.
- Clearly labeled sample-data mode if live data is unavailable.

### Later releases

Add crops and locations after rule review; add soil moisture or soil-property sources after verifying product resolution and coverage; add priority sensitivity, saved history, expert-reviewed pest alerts, forecasts from a dedicated forecast provider, and native apps only when users need them.

### Not in MVP

Pest diagnosis from a photo, guaranteed yield or profit estimates, weather forecasts from historical data, all-crop support, field-level claims from coarse satellite data, and automatic final crop selection.

## 4. User journey

1. Start: explain purpose and limits; offer “Start comparison” or “Try sample field.”
2. Field: enter location, area, irrigation, and optional soil details.
3. History: enter recent crops by season; allow unknown seasons.
4. Goals: select one primary goal—save water, improve rotation/soil, or balance concerns.
5. Analyze: fetch and validate historical climate data; show progress and source.
6. Review: confirm the inputs before evaluation.
7. Compare: view the next-season crop choice for current practice plus up to two alternatives, each evaluated against the same crop history.
8. Understand: open evidence, rules, assumptions, and missing-data details.
9. Decide: save/print the comparison and take it to a local advisor.

Changing inputs creates a new analysis, preserving the inputs and versions used for the previous result.

## 5. System architecture

### Component map

~~~mermaid
flowchart LR
  Farmer --> UI[Responsive Web / PWA]
  UI --> API[Application API]
  API --> Orchestrator[Analysis Orchestrator]
  API --> Field[Field and History Service]
  Orchestrator --> Adapter[Climate Provider Adapter]
  Adapter --> NASA[NASA POWER]
  Adapter --> Quality[Validation, Units, Provenance]
  Quality --> Indicators[Climate Indicator Service]
  Field --> Rules[Agronomic Knowledge Base]
  Indicators --> Engine[Rotation Evaluation Engine]
  Rules --> Engine
  Engine --> Results[Comparison Result]
  Results --> Explain[Evidence Explanation Builder]
  Results --> Store[Result Store]
  Explain --> UI
  Store --> UI
~~~

### What each part does

**Web UI / PWA:** guides the user, collects inputs, shows status/errors and results, and offers print/share. It does not calculate scores or call NASA directly. Use a small initial bundle, lazy-load charts/maps, and preserve form entries when requests fail.

**Application API:** validates requests, coordinates services, and returns typed responses. It keeps provider secrets server-side. Crop science rules do not belong inside web route handlers.

**Field and History Service:** stores the field and user-entered crop seasons, including confidence and unknown values. Missing history remains unknown; it is not inferred.

**Climate Provider Adapter:** converts the app’s location/time/variable request into provider-specific calls and returns normalized observations. Keep provider code isolated so a verified source can later be replaced. For MVP, verify the exact NASA POWER product, variable, endpoint, units, temporal coverage, and terms.

**Validation and Provenance:** checks response structure, date coverage, missingness, plausible ranges, and units. Records source/product, variable, location precision, requested and actual periods, units, retrieval time, quality flags, and processing version.

**Climate Indicator Service:** calculates only defined historical indicators—for example, seasonal rainfall total, baseline mean, anomaly, and variability when data is sufficient. Every indicator specifies formula, units, baseline period, minimum coverage, and interpretation. Insufficient data returns a clear unavailable status.

**Agronomic Knowledge Base:** supplies versioned crop profiles and rotation rules. Each includes conditions, effect, source citation, geographic scope, reviewer, and review status. Only reviewed and geographically applicable rules can affect comparison.

**Candidate Plan Builder:** creates one next-season crop candidate for current practice and up to two alternatives from supported crops. It evaluates each candidate against the recorded crop-season history and may show a derived shorthand such as `wheat → lentil`; the arrow means last season's recorded crop followed by the candidate for next season. The history crop is context, not another planned crop. Invalid options are rejected with a clear reason.

**Rotation Evaluation Engine:** applies hard constraints first, then evaluates supported criteria using climate indicators and reviewed rules. It returns criterion-level evidence and uncertainty, not just a magic number. Missing evidence never improves a plan.

**Explanation Builder:** generates plain-language explanations from engine results and citations. Default MVP should use deterministic templates. Optional AI can paraphrase a fixed evidence package only if it cannot alter results, add unsupported claims, or omit uncertainty. If this cannot be enforced, do not include generative AI.

**Storage and Observability:** stores saved field details only when needed, plus analysis snapshots and data/rule/engine versions. Tracks latency and provider failures without logging unnecessary personal information.

## 6. Data flow

1. UI sends field, history, priority, and live/demo mode.
2. API validates and assigns an analysis ID.
3. Orchestrator requests climate data through the adapter.
4. Validation normalizes units and attaches provenance and quality flags.
5. Indicator service derives eligible historical indicators.
6. Plan builder creates alternatives and applies hard constraints.
7. Evaluation engine assesses each valid plan and links evidence.
8. Explanation builder produces text from those results.
9. API stores a reproducible snapshot and returns it.
10. UI shows plans, evidence, limitations, and data status.

When the provider fails: bounded retries and timeout; use a matching cached response only with its retrieval date shown; otherwise offer sample mode, clearly labeled. Never replace missing values with zero.

### Main data records

- Field: label, approximate location, area/unit, irrigation, optional soil attributes.
- Crop season: field, season/date range, crop or unknown, entry confidence/source.
- Candidate plan: next-season crop, plan type (current practice or alternative), and the history snapshot used to evaluate it. A displayed crop sequence is derived from history plus the candidate; it is not stored as multiple future seasons.
- Crop profile: crop, season, verified attributes, geographic scope, references, version.
- Rotation rule: condition, effect, evidence, reviewer, scope, version, review state.
- Climate dataset: provider/product/variable, location, periods, values/units, retrieval time, quality flags, processing version.
- Analysis: snapshots of inputs, priority, plans, results, limitations, and versions.

## 7. Decision method

Evaluate in this order:

1. Check required inputs and data sufficiency.
2. Reject plans that violate a reviewed hard constraint and explain why.
3. Assess each valid plan against supported criteria.
4. Show evidence and uncertainty for every criterion.
5. Apply the user’s selected priority only to supported criteria.
6. Display trade-offs without concealing conflicts.

Prefer understandable categories such as favorable, mixed, concern, and insufficient evidence over a 0–100 score. If a weighted score is used, show formula, weights, missing criteria treatment, and a clear note that it is not a probability of success.

For each plan, answer:
- What did the system observe?
- Why does it matter, and which rule/source supports that?
- What is uncertain or missing?
- Which decision-relevant inputs were entered, estimated, assumed, or missing, and how does each assumption or gap limit this comparison?
- What should the farmer check locally?

Show these as per-input labels, not a single confidence score: **entered** means supplied by the farmer or team; **estimated** means derived from a named dataset or model; **assumed** means a stated default was used because an input was not supplied; **missing** means the value is unavailable and was not inferred. Show the source or assumption beside each label. If a missing input prevents evaluation, mark the affected criterion "insufficient evidence"; otherwise explain the limitation.

## 8. UI specification: web and mobile

### Platform

Build one responsive web app as an installable PWA for the hackathon. It works on phones and desktop from one codebase and can be added to a phone home screen. Future native Android/iOS apps can use the same API if user research justifies them. Do not build separate APK and web products for the MVP.

### Navigation

Mobile uses a visible stepper: Start → Field → History → Goals → Analyze → Compare. Desktop can use a compact side rail. Back navigation is always available. Keep a local draft so a failed request does not erase user input.

### Screen 1 — Home

- Name and one-sentence product promise.
- Primary button: Start a field comparison.
- Secondary button: Try sample field.
- Brief explanation of what the tool can and cannot do.
- Arabic/English selector only if both translations are complete.
- Avoid large animations and heavy imagery.

### Screen 2 — Field profile

- Optional field name.
- Location search or map pin; typed location must work without loading a map.
- Area with unit selector (dunum, hectare, acre).
- Irrigation: rain-fed, irrigated, mixed, unknown.
- Optional soil type with “I don’t know.”
- Large touch targets, numeric keypad, inline validation, unit shown beside values.
- Lazy-load the map; it must not block form use.

### Screen 3 — Crop history

- One row per season with crop selector and Unknown choice.
- Add/remove season controls.
- Explain that missing history can limit evaluation.
- Confirm entries before continuing; never silently fill gaps.

### Screen 4 — Goals

Choose one primary goal: conserve water, improve soil/rotation, or balance concerns. Optionally select a secondary priority. Avoid free sliders until their scoring effect is validated.

### Screen 5 — Analysis progress

Show stages: checking inputs, retrieving climate data, validating coverage, preparing comparison. Display source and period. Provide retry and sample-data paths. Show a timeout message instead of an endless spinner.

### Screen 6 — Comparison

Desktop: field and data summary, then a readable comparison table/cards for up to three plans. Show criterion labels, one key benefit, one concern, and a “Why?” action. Each plan includes a “What we know” panel with decision-relevant inputs labeled entered, estimated, assumed, or missing; show the source/default and how assumptions or gaps affect that plan.

Mobile: stacked cards, current practice first. Each card shows crop sequence, criterion labels, key benefit, concern, and an evidence button that opens the same “What we know” details. Do not squeeze a desktop table into a narrow screen.

Use text labels as well as color. Provide clear focus, screen-reader labels, semantic headings, and readable contrast. The highlighted summary should state a trade-off, not proclaim an unsupported winner.

### Screen 7 — Evidence

Expandable areas for climate indicator definition, units, source/date range, reviewed rule and citation, and the plan’s “What we know” inputs. For every entered, estimated, assumed, or missing value, show its source or stated default and the effect it has on the result. Include missing-data details and local questions to ask an advisor. Do not show an aggregate confidence score.

### Screen 8 — Save/print

Use a print stylesheet for a one-page comparison. Browser printing is enough for MVP; PDF export is optional. Include report date, data period, and limits. Share links must not expose exact coordinates by default.

### Required UI states

Implement idle, loading, success, partial data, no data, invalid input, provider error, and offline states. Preserve entered form data through retry and navigation.

## 9. Performance, reliability, privacy

### Performance targets (targets, not verified claims)

- Warm mobile load to meaningful content: under 2.5 seconds.
- Initial JavaScript bundle: aim under 200 KB compressed, excluding optional map/chart libraries.
- Cached analysis API response: under 1 second at p95.
- Live analysis: complete within 8 seconds when source responds; otherwise enter a clear timeout state.
- Map is never required to enter a field or view results.
- Cache repeated climate requests by location grid, period, variable, and product with a documented expiry.

### Reliability and security

Use external request timeouts, bounded retries with backoff, and graceful partial results. Never label demo data as live. Keep keys on the server, validate inputs, use HTTPS, restrict saved-field access, avoid exact coordinates in public URLs/logs, and offer deletion if accounts are introduced.

For weak connectivity, cache the app shell and allow a saved report to be viewed offline with its age and source state visible. Charts need text alternatives.

## 10. Suggested build structure and stack

~~~text
field-shift/
  frontend/src/pages/
  frontend/src/components/
  frontend/src/api/
  backend/app/api/
  backend/app/domain/fields.py
  backend/app/domain/rules.py
  backend/app/domain/evaluation.py
  backend/app/services/climate_provider.py
  backend/app/services/validation.py
  backend/app/services/indicators.py
  backend/app/services/explanations.py
  data/demo/
  data/agronomy/
  docs/product-spec.md
  docs/data-dictionary.md
  docs/rule-sources.md
~~~

Choose the frontend framework the team knows best. Python + FastAPI suits the analysis service if Python is familiar. Use plain Python calculations before adding data libraries. SQLite or in-memory storage is sufficient for a demo; choose PostgreSQL when deployment and persistence needs justify it. Use maps and charts only when they add evidence.

### Minimal API

| Method | Route | Purpose |
|---|---|---|
| POST | /api/v1/analyses | Validate and run a comparison |
| GET | /api/v1/analyses/{id} | Retrieve saved result |
| GET | /api/v1/crops | List supported crops |
| GET | /api/v1/demo | Provide clearly labeled sample case |
| GET | /api/v1/health | Deployment health check |

Analysis response includes status, field summary, data source/period/quality, plans, per-plan evidence items with an entered/estimated/assumed/missing state and source or assumption, criterion evidence, limitations, and data/rule/engine versions. It does not include an aggregate confidence score.

## 11. Acceptance criteria

MVP is ready to demonstrate when:
1. The full flow works on phone-sized and desktop screens.
2. Unknown history and missing climate values remain explicit.
3. Live and demo data are visibly distinct.
4. Every indicator has units and date coverage.
5. Every label/score links to a defined calculation or reviewed rule.
6. Invalid plans have a plain-language rejection reason.
7. Changing input creates a new reproducible result.
8. Provider errors preserve the user's form and do not crash the UI.
9. Evidence and limitations can be inspected for every plan.
10. Each plan's “What we know” panel shows decision-relevant inputs as entered, estimated, assumed, or missing, names the source/default, and explains how assumptions or gaps limit the comparison; no aggregate confidence score is shown.
11. The team can state which parts are implemented, simulated, or planned.

Before real-world recommendations, a domain reviewer must check local crop rules; the data lead must verify source product, units, coverage, and resolution; pilot users should review comprehension. Do not claim field validation without doing it.

## 12. Short build plan

**Align:** settle one demo location, three crop sequences, rule citations, and climate variable. Sketch the comparison UI first.

**Build in order:**
1. UI journey with clearly labeled mock data.
2. Shared data models and API contract.
3. Climate adapter, validation, provenance, and fallback.
4. Constraint checks and evidence-linked comparison engine.
5. Connect UI and implement all loading/error states.
6. Mobile polish, print view, and accessibility.
7. Rehearse both live-data and unavailable-data paths.

Assign owners for data, agronomy, backend, UI, and integration/presentation. Every agricultural rule and data claim needs a reviewer.

## 13. Demo narrative

Show one coherent story: a rain-fed field near Hebron has repeated wheat; the user enters what is known and marks unknowns honestly; the app retrieves or loads clearly labeled historical rainfall; three options are compared; “Why?” reveals the climate indicator and a reviewed rotation rule; the user changes the priority and sees the trade-off; the app prints a concise decision brief.

The “wow” is trustworthy clarity: people can see why options differ and what the tool does not know. Avoid claims such as “AI predicts the best crop” or “guaranteed water savings.”

## 14. Decisions — proposed answers

Each row is a proposal. The owner confirms or changes it before coding starts.

| # | Decision | Proposed answer | Owner | Status |
|---|---|---|---|---|
| 1 | Pilot location and precision | One representative rain-fed field near Hebron. Coordinates rounded to 0.1° (about 31.5 N, 35.1 E) everywhere: storage, URLs, logs, report. The climate grid cell is far larger than 0.1°, so rounding loses nothing. | Data | Proposed |
| 2 | Crops and plans | Each plan is one next-season crop candidate evaluated against the same recorded crop history. With wheat recorded in the immediately preceding season: (A) wheat → wheat (repeat current practice), (B) wheat → lentil, (C) wheat → vetch. The left crop is history context, not an extra planned season. If the immediately preceding season is unknown, show it as unknown and do not infer a current-practice crop. Rules in section 18. No local reviewer is confirmed yet, so every rule ships with review state `draft-unreviewed` and the UI shows that label. | Agronomy | Needs reviewer |
| 3 | NASA POWER details | See section 16. Daily point API, variable `PRECTOTCORR`, community `AG`, mm/day. | Data | Verify with one live call |
| 4 | Minimum history | Evaluate each next-season candidate against the recorded seasons immediately before it. The repeated-cereal rule needs enough consecutive known history to confirm or rule out a three-cereal run (at most the two preceding seasons); the legume-after-cereal rule needs the immediately preceding season known. An unknown season that prevents either decision → "insufficient evidence", never a guess. | Agronomy | Proposed |
| 5 | Ratings | Ordinal only: favorable, mixed, concern, insufficient evidence. No 0–100 score in the MVP. The selected goal changes the order criteria are shown in and which trade-off the summary names; it does not change any label. | Backend | Proposed |
| 6 | Language | One UI language for the demo. Arabic if the RTL layout is complete by the integration checkpoint; otherwise English. No half-translated selector. Submission text and slides in English. | UI | Proposed |
| 7 | Persistence | Session only, no accounts. Analysis snapshots in SQLite keyed by analysis ID. Form draft in browser local storage. | Backend | Proposed |
| 8 | Deployment and test device | Static frontend host plus one small FastAPI instance. Test on one mid-range Android phone in Chrome and one desktop browser. | Integration | Proposed |
| 9 | Generative AI | None in the MVP. Explanations come from deterministic templates filled from engine output (section 5, Explanation Builder). A paraphrasing layer is later work. | Backend | Proposed |

### In-app notice

“Field Shift compares options using the information and sources shown. Gridded climate data may not represent conditions within your exact field, and historical conditions do not predict next season. Review choices with local agricultural expertise.”

## 15. Final MVP definition

A responsive web/PWA that takes one field, its known crop history, a selected goal, and verified historical rainfall context; compares up to three plans using a small locally reviewed rule set; and shows the evidence, trade-offs, and uncertainty in plain language.

Additional data sources, advanced AI, pest reporting, predictive models, and native apps are future work that depends on validation and user need.

## 16. Data dictionary — climate source

| Item | Value | Confidence |
|---|---|---|
| Provider | NASA POWER (Prediction Of Worldwide Energy Resource), NASA Langley Research Center | Confirmed |
| Temporal API | Daily, single point | Confirmed |
| Community | `AG` (agroclimatology) | Confirmed |
| Variable | `PRECTOTCORR` — MERRA-2 bias-corrected precipitation | Confirmed |
| Units | mm/day | Confirmed |
| Grid resolution | 0.5° latitude × 0.625° longitude (MERRA-2 meteorology) | Confirmed |
| Endpoint | `https://power.larc.nasa.gov/api/temporal/daily/point` | Verify with a live call |
| Query parameters | `parameters=PRECTOTCORR&community=AG&latitude=31.5&longitude=35.1&start=YYYYMMDD&end=YYYYMMDD&format=JSON` | Verify with a live call |
| Response path | `properties.parameter.PRECTOTCORR` → map of `YYYYMMDD` → value | Verify with a live call |
| Missing-value marker | `-999` (read the actual fill value from the response header; treat it as missing, never as rain) | Verify with a live call |
| API key | None expected | Verify with a live call |
| Period requested | 1 Oct 1990 to 31 May 2026 | Team choice |
| Rate limits and terms | Read https://power.larc.nasa.gov/docs/services/api/ before the demo; cache every response | To do |

**Resolution warning for the UI:** one grid cell is roughly 55 km × 60 km at this latitude. It covers the Hebron hills and land well beyond them, which differ a lot in rainfall. The app reports the cell value as regional context and says so on the evidence screen.

**Acknowledgement line for the report and slides:** “The data was obtained from the National Aeronautics and Space Administration (NASA) Langley Research Center (LaRC) Prediction of Worldwide Energy Resource (POWER) Project funded through the NASA Earth Science/Applied Science Program.”

**Provenance record stored with each dataset:** provider, variable, community, rounded latitude/longitude, requested start/end, actual first/last date returned, count of valid days, count of missing days, units, retrieval timestamp (UTC), adapter version.

## 17. Indicator definitions

A **season** is 1 October of year Y to 31 May of year Y+1, labelled Y/Y+1. This is the team's working definition of the rain-fed winter season; the agronomy owner confirms it.

| Indicator | Formula | Units | Minimum coverage | If not met |
|---|---|---|---|---|
| Seasonal rainfall total | Sum of daily `PRECTOTCORR` over the season | mm | At least 95% of the season's days valid | Season marked unavailable and excluded |
| Baseline mean | Mean of seasonal totals for 1991/92 to 2020/21 | mm | At least 24 of 30 seasons valid | Indicator unavailable |
| Season anomaly | (season total − baseline mean) ÷ baseline mean × 100 | % | Season and baseline both valid | Unavailable |
| Variability (CV) | Standard deviation of baseline seasonal totals ÷ baseline mean × 100 | % | Same as baseline mean | Unavailable |
| Seasons meeting a threshold | Count of valid baseline seasons with total ≥ threshold T, shown as "n of N" | count | Same as baseline mean | Unavailable |

Rules for all indicators: missing days are excluded from sums and counted separately; the valid-day count is displayed beside every total; every value is labelled "historical", never "expected" or "forecast".

## 18. Draft rule set (version 0.1, `draft-unreviewed`)

**Nothing in this section has been reviewed by an agricultural specialist.** Citations name where support should be found; the agronomy owner must locate the exact document and page and record it in `docs/rule-sources.md` before a rule's status changes. Until then the comparison screen carries a visible "illustrative rules, not reviewed" label.

### Crop profiles

| Crop | Type | Season | Indicative seasonal water need | Source to confirm |
|---|---|---|---|---|
| Wheat | Cereal | Winter, rain-fed | 450–650 mm | FAO Irrigation Water Management Training Manual No. 3, crop water needs table |
| Lentil | Grain legume | Winter, rain-fed | No confirmed figure. FAO lists pea at 350–500 mm; whether that applies to lentil is a reviewer question | ICARDA / FAO, to locate |
| Vetch | Forage legume | Winter, rain-fed | No confirmed figure | ICARDA forage legume publications, to locate |

A crop with no confirmed water figure gets "insufficient evidence" on water fit. It does not inherit another crop's number.

### Hard constraints (checked first; a failure rejects the plan with a reason)

| ID | Condition | Rejection reason shown |
|---|---|---|
| H1 | Plan contains a crop that is not in the supported crop list | "This crop is not supported in this version." |
| H2 | Plan contains a crop whose profile season does not match the planned season | "This crop is not grown in the selected season in this version." |
| H3 | Plan contains a crop marked irrigated-only while the field is rain-fed | "This crop needs irrigation; the field is recorded as rain-fed." |

None of the three MVP crops trips H2 or H3; they exist so the rejection path is real and can be shown with a fourth, deliberately invalid sample plan.

### Criterion rules

All plans are next-season crop candidates appended to the recorded crop history. “Previous season” means the immediately preceding season in that history; do not skip unknown seasons to find an older crop. For display, `wheat → lentil` means wheat was recorded in the immediately preceding season and lentil is the next-season candidate. If that season is unknown, display `unknown → lentil`.

| ID | Criterion | Condition | Result | Rationale to confirm | History needed |
|---|---|---|---|---|---|
| R1 | Rotation / soil | Candidate is a cereal and, counting backward from the immediately preceding season, it would complete a run of 3 or more consecutive cereal seasons | Concern | Continuous cereal is associated with build-up of cereal diseases and weeds and with soil nitrogen drawdown | Inspect up to the 2 immediately preceding seasons. A known non-cereal breaks the run; an unknown before the run can be confirmed or broken makes the result insufficient evidence. |
| R2 | Rotation / soil | Candidate is a legume and the immediately preceding season was a cereal | Favorable | Legumes fix nitrogen and interrupt cereal disease cycles | Immediately preceding season known |
| R3 | Rotation / soil | Neither R1 nor R2 applies and available history is sufficient to assess them | Mixed | No specific rotation effect identified | Sufficient contiguous history to rule out R1 and assess R2 |
| R4 | Water fit | Crop has a confirmed lower water bound T. Share of valid baseline seasons with total ≥ T: 80% or more → favorable; 50% to under 80% → mixed; under 50% → concern | As computed | Compares historical seasonal rainfall with the crop's indicative need | None (uses climate data) |
| R5 | Water fit | Crop has no confirmed water figure, or field irrigation is "unknown", or baseline unavailable | Insufficient evidence | — | — |
| R6 | Risk | Baseline CV: under 20% → favorable; 20% to 35% → mixed; over 35% → concern. Same label for all plans at one location; it describes the place, not the crop | As computed | Higher year-to-year rainfall variability means a less dependable season | None |

The 80/50 and 20/35 cut-offs are team choices made so that labels are reproducible. They are not agronomic standards and are shown as such on the evidence screen.

When required history is unknown, R1–R3 return "insufficient evidence". Do not infer a crop from an older season across an unknown season. The current-practice candidate repeats only a crop recorded in the immediately preceding season; otherwise that option is unavailable until the user chooses a candidate.

### Local questions printed on every report

- Does rainfall at your field differ from the wider area shown here?
- Is there a buyer or a use for lentil or vetch near you, and at what price?
- Are seed and suitable harvesting equipment available for the alternative crop?
- What has your agricultural extension officer seen with these rotations locally?

### Explanation templates

- Rotation concern (R1): "This plan would be the {n}th cereal season in a row on this field. Draft rule R1 flags this as a rotation concern. Rule status: not yet reviewed."
- Rotation benefit (R2): "{crop} is a legume following a cereal. Draft rule R2 marks this as a rotation benefit. Rule status: not yet reviewed."
- Water fit (R4): "In {n} of {N} past seasons ({first}–{last}), rainfall for this area reached {T} mm, the lower indicative need for {crop}. Area data is from one NASA POWER grid cell and may not match your field."
- Insufficient: "We could not assess {criterion} for this plan because {reason}. This is not a negative result."

## 19. Implemented, simulated, planned

Keep this table current during the build; it answers acceptance criterion 11 and goes on the last slide.

| Part | State at start of build | Target for demo |
|---|---|---|
| UI journey, all eight screens | Planned | Implemented |
| NASA POWER adapter, validation, provenance | Planned | Implemented, with cached sample fallback |
| Indicators (section 17) | Planned | Implemented |
| Rule engine (section 18) | Planned | Implemented |
| Rule content | Draft, unreviewed | Simulated — labelled illustrative unless a reviewer signs off |
| Lentil and vetch water figures | Missing | Shown as insufficient evidence unless sourced |
| Print report | Planned | Implemented via browser print |
| Offline saved report, PWA install | Planned | Implemented if time allows; otherwise stated as planned |
| Arabic interface | Planned | Per decision 6 |
| Field validation with farmers | Not done | Not done — stated plainly |

