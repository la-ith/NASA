# Field Shift — Product and System Specification

Version 3.2 | 14 November 2026 | NASA Space Apps Challenge 2026 — "Field Shift: Adapting Farms with NASA Data" | Proposed build plan

**Status:** This specification describes intended behavior, not completed features. Items marked MVP are the recommended hackathon build. Other items are later releases. Everything marked "proposed" is a team proposal until the named owner confirms it.

**Changes in 3.2.** Checked against the challenge Details and Resources tabs, the Space Apps Project Submission and Judging & Awards guides, FAO Training Manual No. 3, and a live NASA POWER call made on 14 November 2026.

- The MVP now compares **at least three** plans, including current practice. The challenge asks for at least three strategies including the existing rotation; v3.1 said "up to three".
- Each plan now states why it was included, its benefits, its evidence, information gaps, and risks to review locally. These five items are named in the challenge objectives.
- NASA POWER details are now verified by a live call, not assumed (section 16).
- The live data shows that the pilot grid cell gets about half the rainfall recorded at Hebron station. A new site check (section 16.1) stops that bias from producing a misleading water-fit label.
- Fixed contradictions in v3.1:
  - Section 1 and section 5 allowed only reviewed rules, while section 14 and section 18 ship draft rules.
  - Hard constraints were applied by two different components.
  - The Review step was missing from the stepper and the screens.
  - The component map left out the Plan Builder, and the UI took results without going through the API.
  - Water fit was undefined for irrigated or mixed fields.
  - The R1 explanation said "{n}th" although only two seasons are inspected.
  - The data period did not match the baseline.
  - A secondary goal was allowed, against section 14.
- Added these diagrams: an analysis flowchart (6.1), an analysis state diagram (6.2), a rotation-rule flowchart (18), and a rule-review state diagram (18).
- Added these specifications: input validation (6.3), label meanings (7), a recent-shift indicator (17), a concrete sample history and expected results (18), and an API example (10).
- Added three new sections: challenge coverage (20), submission checklist (21), and glossary (22).
- Replaced the NASA POWER acknowledgement with the current official wording.

## 1. Vision

Field Shift helps a farmer compare crop rotation options for one field. It uses historical climate context from NASA data and transparent, locally reviewed agricultural rules.

**Promise:** Compare options, see why they differ, understand the evidence and uncertainty, and make an informed decision with local expertise.

It is decision support. It is not a yield guarantee, a weather forecast, or a replacement for an agronomist.

### First user and demo case

Primary user: a smallholder farmer or advisor planning the next season for a rain-fed field.

Demo scenario: a representative rain-fed field near Hebron. The recorded history is:

| Season | Crop |
|---|---|
| 2023/24 | unknown |
| 2024/25 | wheat |
| 2025/26 | wheat |

For the 2026/27 season, the app compares three plans:

- (A) wheat again, as current practice
- (B) lentil
- (C) vetch

All three are evaluated against the same recorded history. Until a local agricultural reviewer confirms the rules, every comparison carries the label "illustrative rules, not reviewed" (section 18). The demo is illustrative until data and agronomy are verified.

### What success looks like

A user can:

- enter a field and its crop history
- see the coverage, quality and local fit of the climate data
- compare at least three plans, including current practice
- understand each trade-off and limitation
- save or print the comparison

## 2. Product principles

1. **Evidence first:** every indicator and agricultural rule has a definition, source, units, and applicable region.
2. **Honest uncertainty:** missing data is never zero, and historical conditions are never called a forecast.
3. **Check the data fits the place:** absolute climate values are used for a decision only after they have been checked against a local record (section 16.1).
4. **Rules calculate; explanations explain:** generative AI ("SI" in Space Apps 2026 terms) cannot change results or invent agricultural facts.
5. **Keep the first release narrow:** one pilot area, a few crops, one verified climate source.
6. **The farmer chooses:** the app displays trade-offs rather than silently deciding.
7. **Mobile first** and friendly to low bandwidth.
8. **A complete, credible workflow** is better than many unfinished features.

## 3. Scope

### MVP — build for the hackathon

- A responsive web application that can be installed as a PWA.
- One pilot area (section 6.3) and one sample field.
- Field details: approximate location, area, irrigation, and optional soil type. Soil type is displayed as entered context; no MVP rule uses it.
- Recent crop history, with an explicit unknown option.
- One verified source for historical rainfall: NASA POWER `PRECTOTCORR` (section 16).
- A site check that compares the NASA POWER cell with a local station record (section 16.1).
- Data validation, units, source, version and date range, all shown to users.
- A small crop and rotation rule set with citations. Every rule is labelled draft until an agricultural domain reviewer approves it.
- At least three plans: current practice plus two alternatives.
- Hard constraints are checked before plans are compared.
- Comparison on three criteria: water fit, rotation/soil, and rainfall-variability risk.
- Explanations linked to evidence, with visible limitations.
- A print-friendly comparison report.
- A clearly labelled sample-data mode for when live data is unavailable.

### Later releases

Section 20 lists each NASA dataset, the reason it is deferred, and the precondition for adding it.

- More crops and locations, after rule review.
- GPM IMERG rainfall at 0.1° (about 10 km).
- SMAP soil moisture.
- ECOSTRESS evapotranspiration.
- Landsat, MODIS or Sentinel-2 vegetation indices for bare-field periods.
- SRTM slope for erosion risk.
- Temperature-based frost and heat indicators with an elevation adjustment.
- Market and equipment constraints as user inputs.
- Multi-season rotation plans.
- Saved history.
- Expert-reviewed pest alerts.
- Native apps, only when users need them.

### Not in MVP

- Pest diagnosis from a photo.
- Guaranteed yield or profit estimates.
- Weather forecasts from historical data.
- Support for all crops.
- Field-level claims from coarse gridded data.
- Temperature-based crop labels (see section 20).
- Automatic final crop selection.

## 4. User journey

1. **Start:** explain the purpose and limits; offer "Start a field comparison" or "Try sample field".
2. **Field:** enter location, area, irrigation, and optional soil type.
3. **History:** enter recent crops by season; seasons can be marked unknown.
4. **Goal:** select one goal: conserve water, improve soil and rotation, or balance both.
5. **Review:** confirm all inputs before anything is fetched or evaluated.
6. **Analyze:** fetch and validate historical climate data; show progress and the source.
7. **Compare:** view the three plans for the next season, each evaluated against the same crop history.
8. **Understand:** open the evidence, rules, assumptions, site check, and missing-data details.
9. **Decide:** save or print the comparison and take it to a local advisor.

Changing any input, including the goal, creates a new analysis with its own ID. Earlier analyses stay unchanged, with the inputs and versions they used. Cached climate data is reused, so re-running is fast.

## 5. System architecture

### Component map

Solid arrows show data flow. Dotted arrows show the orchestrator calling a component.

~~~mermaid
flowchart LR
  User(["Farmer or advisor"]) --> UI["Web app / PWA"]
  UI -->|"request: field, history, goal, mode"| API["Application API"]
  API -->|"response: plans, evidence, limits"| UI
  API -.-> Orch["Analysis Orchestrator"]
  Orch -.-> FieldSvc["Field and History Service"]
  Orch -.-> Adapter["Climate Provider Adapter"]
  Orch -.-> Builder["Candidate Plan Builder"]
  Orch -.-> Engine["Rotation Evaluation Engine"]
  POWER["NASA POWER Daily API"] --> Adapter
  Sample[("Labelled sample record")] --> Adapter
  Adapter <--> Cache[("Climate cache")]
  Adapter --> Valid["Validation, units, provenance, site check"]
  Valid --> Ind["Climate Indicator Service"]
  FieldSvc --> Builder
  KB[("Agronomic Knowledge Base")] --> Builder
  KB --> Engine
  Builder --> Engine
  Ind --> Engine
  Engine --> Explain["Explanation Builder"]
  Explain --> Store[("Result Store")]
  Store --> API
~~~

### What each part does

**Web UI / PWA:** guides the user, collects inputs, shows status, errors and results, and offers print and share. It talks only to the Application API. It never calculates labels and never calls NASA directly. Keep the initial bundle small, lazy-load maps and charts, and keep form entries when a request fails. The UI rounds coordinates to 0.1° before sending them.

**Application API:** validates requests (section 6.3), assigns analysis IDs, and returns typed responses. It keeps provider settings on the server. Crop science rules do not belong in route handlers.

**Analysis Orchestrator:** runs the steps of one analysis in a fixed order (section 6.1), enforces the time limits, and records the analysis state (section 6.2).

**Field and History Service:** stores the field and the crop seasons the user entered, including unknown values. A season that was not entered counts as unknown. Missing history is never inferred.

**Climate Provider Adapter:** turns the app's location, period and variable request into a NASA POWER call and returns normalized daily values. It reads the cache before calling the provider and writes successful responses to it. It handles HTTP 422, 429, 5xx and timeouts as described in section 6. Provider code stays isolated so a verified source can later be added or swapped.

**Validation, units, provenance, site check:**

- Checks response structure, units, the fill value, date coverage, and plausible ranges.
- Records provenance (section 16).
- Runs the site check (section 16.1).

**Climate Indicator Service:** calculates only the indicators defined in section 17. If the data is insufficient, it returns an "unavailable" status, never a number.

**Agronomic Knowledge Base:** holds versioned crop profiles, history crop types, hard constraints and criterion rules. Each item records:

- conditions and effect
- citation
- geographic scope
- reviewer
- review state

There are three review states: `draft-unreviewed`, `reviewed` and `retired`; section 18 has the lifecycle diagram.

- A `retired` rule never applies.
- During the hackathon demo, a `draft-unreviewed` rule may apply only if every result it affects shows the label "illustrative rules, not reviewed".
- Beyond the demo, only `reviewed` rules whose scope covers the field may apply.

**Candidate Plan Builder:** builds the plans for the next season and records why each one was included.

- **Plan A (current practice)** repeats the crop recorded in the immediately preceding season. If that season is unknown, or its crop is not a supported candidate, the user picks the crop for Plan A.
- **Plans B and C** are the other two supported candidate crops. In the MVP there are three supported candidates (wheat, lentil, vetch), so this always yields exactly three plans.
- **Plan D** exists in the sample case only. It is a deliberately unsupported crop (maize) that demonstrates the rejection path.

A plan can be displayed as `wheat → lentil`. The left crop is the immediately preceding season from history, shown as context. The right crop is the candidate for next season. Only one future season is planned.

**Rotation Evaluation Engine:** the only component that applies hard constraints and criterion rules. It applies constraints H1–H3 first; a plan that fails is rejected with a plain-language reason. It then applies rules R1–R6 to each remaining plan. The result is one label per criterion, with evidence and uncertainty, not a single score. Missing evidence never improves a plan.

**Explanation Builder:** fills fixed templates (section 18) from the engine output. The MVP uses no generative AI (decision 9).

**Storage and Observability:** stores analysis snapshots: inputs, provenance, site-check result, and the versions of rules, engine and adapter. It tracks latency and provider failures without logging exact locations or other unnecessary personal information.

## 6. Data flow

1. The UI sends the field (rounded location), history, goal, candidate season and mode (live or sample).
2. The API validates the input (section 6.3).
   - If the input is invalid, it returns HTTP 422 with an error per field.
   - Otherwise it assigns a random analysis ID and saves an input snapshot.
3. The orchestrator asks the adapter for climate data.
   - Sample mode uses the labelled sample record.
   - Live mode uses the cache if a matching entry exists, and otherwise calls NASA POWER.
4. Validation converts fill values to missing, checks units and coverage, attaches provenance and quality flags, and runs the site check.
5. The indicator service calculates the section 17 indicators.
6. The plan builder creates Plans A–C, plus Plan D in sample mode.
7. The evaluation engine applies H1–H3, then R1–R6, and links evidence to each label.
8. The explanation builder fills the templates.
9. The API stores the snapshot and returns it.
10. The UI shows the plans, evidence, limitations, site check and data status.

**When the provider fails:**

- Each attempt times out after 10 seconds.
- On a timeout, HTTP 429 or HTTP 5xx, the adapter retries once after 2 seconds.
- HTTP 422 is never retried, because it means the request itself is wrong.
- After the second failure, the UI shows the provider-error state with two choices: "Retry" (a fresh attempt sequence) or "Use sample data" (clearly labelled).
- A cached response is used only if it matches the request, and its retrieval date is shown.
- Missing values are never replaced with zero.

**Cache warm-up:** at deploy time, fetch and store the pilot cell's full record. The demo then does not depend on a live call succeeding.

### Main data records

- **Field:** label, rounded location, area and unit, irrigation, optional soil type.
- **Crop season:** field, season label (for example 2025/26), crop or unknown, and the entry source.
- **Candidate plan:** plan ID (A–D), next-season crop, plan type (current practice, alternative or sample test), the reason it was included, and the history snapshot used to evaluate it. A displayed crop sequence is derived from history plus the candidate; it is not stored as several future seasons.
- **Crop profile:** crop, type, season, verified attributes, geographic scope, references, version, review state.
- **Rule:** ID, condition, effect, evidence, reviewer, scope, version, review state.
- **Climate dataset:** provider, API version, parameter, community, rounded location, cell elevation, requested and actual periods, values and units, retrieval time (UTC), quality flags, site-check result, adapter version.
- **Analysis:** ID, state (section 6.2), and snapshots of inputs, goal, plans, results, limitations and versions.

### 6.1 Analysis flowchart

This flowchart shows one analysis, from the Review screen to the result.

~~~mermaid
flowchart TD
  A(["User taps Run analysis on the Review screen"]) --> B{"Inputs valid?"}
  B -->|"No"| B1["Show invalid-input messages; keep the form data"]
  B1 --> B2(["User fixes the problem and runs again"])
  B -->|"Yes"| ON{"Device online?"}
  ON -->|"No"| OFF["Offline state: keep the form; saved reports stay viewable"]
  OFF --> B2
  ON -->|"Yes"| C["Create analysis ID and input snapshot"]
  C --> D{"Mode?"}
  D -->|"Sample"| S["Load labelled sample record"]
  D -->|"Live"| E{"Matching cache entry?"}
  E -->|"Yes"| V
  E -->|"No"| F["Call NASA POWER daily point API"]
  F --> G{"Result of the call"}
  G -->|"HTTP 200 within 10 s"| H["Save response to cache"]
  H --> V
  G -->|"HTTP 422"| P
  G -->|"Timeout, 429 or 5xx"| R{"Retry already used?"}
  R -->|"No"| R1["Wait 2 s"]
  R1 --> F
  R -->|"Yes"| P["Provider-error state: offer Retry or Use sample data"]
  P -->|"Retry"| F
  P -->|"Use sample data"| S
  S --> V["Validate: structure, units, fill value to missing, coverage, plausible range"]
  V --> W{"Usable record?"}
  W -->|"No"| N["No-data state: explain why; offer sample data"]
  N -->|"Use sample data"| S
  W -->|"Yes"| X["Site check: grid cell vs local station (16.1)"]
  X --> I["Compute indicators (17)"]
  I --> K["Build candidate plans A, B, C (and D in sample mode)"]
  K --> L{"For each plan: passes H1 to H3?"}
  L -->|"No"| L1["Mark plan rejected with reason"]
  L -->|"Yes"| O["Apply R1 to R6: one label and evidence per criterion"]
  L1 --> Q["Fill explanation templates"]
  O --> Q
  Q --> T["Save reproducible snapshot"]
  T --> U{"Any criterion with insufficient evidence, or any data flag?"}
  U -->|"Yes"| U1(["Show comparison with partial-data notice"])
  U -->|"No"| U2(["Show comparison"])
~~~

### 6.2 Analysis state diagram

Every analysis is in exactly one of these states. The UI shows one screen state for each.

~~~mermaid
stateDiagram-v2
  [*] --> Draft
  Draft --> Draft : edit inputs (draft saved in the browser)
  Draft --> InvalidInput : run with invalid inputs
  InvalidInput --> Draft : user corrects inputs
  Draft --> Offline : run while the device is offline
  Offline --> Draft : connection restored
  Draft --> Fetching : run in live mode
  Draft --> Validating : run in sample mode
  Fetching --> Validating : HTTP 200 or cache hit
  Fetching --> Retrying : first timeout, 429 or 5xx
  Retrying --> Fetching : after 2 s
  Fetching --> ProviderError : HTTP 422 or second failure
  ProviderError --> Fetching : user retries
  ProviderError --> Validating : user chooses sample data
  Validating --> NoData : record unusable
  NoData --> Validating : user chooses sample data
  Validating --> Evaluating : record usable
  Evaluating --> Complete : every criterion assessed
  Evaluating --> Partial : at least one criterion has insufficient evidence
  Complete --> Draft : user changes an input (new analysis ID)
  Partial --> Draft : user changes an input (new analysis ID)
  Complete --> [*]
  Partial --> [*]
~~~

| Analysis state | UI state (section 8) | What the user sees |
|---|---|---|
| Draft | idle | Form steps; draft kept in the browser |
| InvalidInput | invalid input | Inline messages on the fields to fix |
| Offline | offline | "You are offline." Saved reports can still be opened, with their age shown |
| Fetching, Retrying, Validating, Evaluating | loading | Progress stages, source and period; a "Use sample data" link is always available |
| ProviderError | provider error | What failed, with Retry and Use sample data |
| NoData | no data | Why the record is unusable, with Use sample data |
| Complete | success | Comparison |
| Partial | partial data | Comparison with a notice listing what could not be assessed and why |

In the pilot, every live analysis ends in **Partial**. The site check fails, and lentil and vetch have no confirmed water figure, so water fit is "insufficient evidence" for all plans (section 18, expected results).

### 6.3 Input validation

| Input | Rule | Error shown |
|---|---|---|
| Location | Must round to 31.5 N, 35.1 E. That is, latitude from 31.45 up to but not including 31.55, and longitude from 35.05 up to but not including 35.15. This is the MVP pilot area. The UI rounds to 0.1° before sending; the API rejects values with more than one decimal place. | "This version supports only the Hebron pilot area." |
| Area | Number greater than 0, with unit dunum, hectare or acre. Display only; no MVP calculation uses it. 1 dunum = 1,000 m² = 0.1 ha. | "Enter an area greater than zero." |
| Irrigation | One of: rain-fed, irrigated, mixed, unknown | "Choose an irrigation type." |
| Soil type | Optional free choice or "I don't know"; display only | — |
| History | From 1 to 5 seasons. Contiguous. The last one is the season immediately before the candidate season (2025/26 for 2026/27). Each season has exactly one choice from the history crop list (section 18) or "unknown". | "Seasons must be consecutive and end with 2025/26." |
| Goal | One of: conserve water, improve soil and rotation, balance both | "Choose one goal." |
| Mode | `live` or `sample` | — |

## 7. Decision method

Evaluate in this order:

1. Check required inputs and data sufficiency.
2. Reject plans that violate a hard constraint (H1–H3), and explain why.
3. Assess each remaining plan against the three criteria (R1–R6).
4. Show the evidence and uncertainty for every criterion.
5. Use the selected goal only to order criteria and to choose which trade-off the summary names. The goal never changes a label.
6. Display trade-offs without hiding conflicts.

The MVP uses ordinal labels only. There is no 0–100 score and no weighted total (decision 5).

| Label | Meaning |
|---|---|
| Favorable | A rule identifies a benefit for this criterion and no concern |
| Mixed | The criterion was assessed, but no clear benefit or concern was found, or the evidence points both ways |
| Concern | A rule identifies a problem for this criterion |
| Insufficient evidence | The criterion could not be assessed. This is not a negative result |

| Goal | Criterion order | Summary names |
|---|---|---|
| Conserve water | Water fit, Risk, Rotation/soil | How plans differ on water fit, or why it could not be assessed |
| Improve soil and rotation | Rotation/soil, Water fit, Risk | How plans differ on rotation/soil |
| Balance both | Water fit, Rotation/soil, Risk | The largest difference across water fit and rotation/soil |

The summary sentence names the highest-priority criterion on which plans differ, and each plan's label on it. It also names any criterion that could not be assessed for any plan. If no assessed criterion differs, it says so. It never names a "best" plan.

For each plan, the comparison and evidence screens answer five questions. These are the five items the challenge asks for.

1. **Why is it included?** For example: "Current practice: repeats the crop recorded for 2025/26", or "Alternative: a supported grain legume for the 2026/27 winter season".
2. **What evidence was used?** The climate indicators with source and period, and the recorded history.
3. **What are the benefits and concerns?** One label per criterion, each with the rule and its citation.
4. **What is uncertain or missing?** Each decision-relevant input is labelled entered, estimated, assumed, or missing, and the panel says how each gap limits the comparison.
5. **What should be checked locally?** The local questions (section 18) and any rule still in draft.

The input labels mean:

- **Entered:** supplied by the farmer or the team.
- **Estimated:** derived from a named dataset or model.
- **Assumed:** a stated default used because an input was not supplied.
- **Missing:** unavailable and not inferred.

Show the source or default beside each label. If a missing input prevents an evaluation, that criterion is "insufficient evidence". Otherwise, explain the limitation. Do not show an overall confidence score.

## 8. UI specification: web and mobile

### Platform

Build one responsive web app as an installable PWA for the hackathon. It works on phones and desktops from one codebase and can be added to a phone home screen. Future native Android and iOS apps can use the same API if user research justifies them. Do not build separate APK and web products for the MVP.

### Navigation

Mobile uses a visible stepper: Start → Field → History → Goal → Review → Analyze → Compare. Desktop can use a compact side rail. Back navigation is always available. A local draft is kept so a failed request does not erase user input.

### Screen 1 — Home

- Name and the one-sentence product promise.
- Primary button: Start a field comparison.
- Secondary button: Try sample field.
- A brief explanation of what the tool can and cannot do, plus the in-app notice (section 14).
- One UI language (decision 6). No language selector unless both translations are complete.
- No large animations or heavy imagery.

### Screen 2 — Field profile

- Optional field name.
- Location search or map pin. Typed location must work without loading a map. Show the rounded location the app will use.
- Area with a unit selector: dunum, hectare, acre.
- Irrigation: rain-fed, irrigated, mixed, unknown.
- Optional soil type, with "I don't know".
- Large touch targets, a numeric keypad, inline validation, and the unit shown beside values.
- Lazy-load the map; it must not block use of the form.

### Screen 3 — Crop history

- One row per season, labelled like 2025/26. The latest season is prefilled.
- Each row has a crop selector with the history crop list (section 18) and an Unknown choice.
- Controls to add and remove seasons, up to 5.
- Explain that missing history can limit the evaluation.
- Never fill gaps silently.

### Screen 4 — Goal

Choose one goal: conserve water, improve soil and rotation, or balance both. Explain in one line that the goal changes the order of criteria and the summary, not the labels. No secondary goal and no sliders in the MVP.

### Screen 5 — Review

- A read-only summary of every input, each with an "Edit" link back to its step.
- The rounded location, the mode (live or sample), and the plans that will be compared.
- Primary button: Run analysis.

### Screen 6 — Analysis progress

- Stages: checking inputs, retrieving climate data, validating coverage, checking the data against the local station, preparing the comparison.
- Show the source and period.
- Offer Retry and Use sample data.
- Show a timeout message instead of an endless spinner.

### Screen 7 — Comparison

- **Banners at the top, as they apply:**
  - "Sample data" whenever sample mode is used.
  - "Illustrative rules, not reviewed" while any rule used is `draft-unreviewed`.
- **Desktop layout:**
  - a field and data summary, including the site-check result
  - a readable table or set of cards for the three plans
  - for each plan, its "why included" line, criterion labels, one key benefit, one concern, and a "Why?" action
  - for each plan, a "What we know" panel with inputs labelled entered, estimated, assumed or missing, the source or default, and the effect on that plan
- **Mobile layout:**
  - stacked cards, current practice first
  - each card shows the crop sequence, why it was included, criterion labels, key benefit, concern, and an evidence button that opens the same "What we know" details
  - do not squeeze a desktop table onto a narrow screen
- **Rejected plans:** Plan D in sample mode is shown below the others as "Not evaluated", with its rejection reason.
- **Accessibility:**
  - use text labels as well as color
  - aim for WCAG 2.2 AA contrast
  - provide visible focus, screen-reader labels and semantic headings
- **Summary:** the highlighted summary states a trade-off (section 7), never an unsupported winner.

### Screen 8 — Evidence

Expandable areas for:

- each climate indicator's definition, units, source, API version, period and valid-day count
- the site check: cell value against the station value, cell elevation against field elevation, and the outcome
- each rule's text, citation, review state and cut-offs, with team-chosen cut-offs marked as such
- the plan's "What we know" inputs, each with its source or default and its effect on the result
- missing-data details
- questions to ask a local advisor

Do not show an overall confidence score.

### Screen 9 — Save and print

- Use a print stylesheet for a one-page comparison. Browser printing is enough for the MVP; PDF export is optional.
- The report includes:
  - the report date and data period
  - the site-check result
  - the limits
  - the rule review state
  - the local questions
  - the NASA POWER acknowledgement and data reference (section 16)
- Share links never contain coordinates. They carry only the random analysis ID.

### Required UI states

Implement idle, loading, success, partial data, no data, invalid input, provider error, and offline. Section 6.2 maps each one to an analysis state. Keep entered form data through retries and navigation.

## 9. Performance, reliability, privacy

### Performance targets

These are targets, not verified claims.

- Warm mobile load to meaningful content: under 2.5 seconds.
- Initial JavaScript bundle: under 200 KB compressed, excluding optional map and chart libraries.
- Analysis from a cached climate record: under 1 second at p95.
- Live analysis: under 8 seconds when the provider responds; otherwise enter the timeout state.
  - Measured on 14 November 2026: one `PRECTOTCORR` request for 1 Oct 1991 to 31 May 2026 took 2.3–2.8 seconds.
  - The same period with three parameters took 10.9 seconds.
  - So the MVP requests only `PRECTOTCORR`.
- A map is never required to enter a field or view results.
- Climate cache:
  - Key: rounded latitude and longitude, parameter, community, start date, end date, and API version.
  - Expiry: 30 days. Historical values can change when POWER releases a new version.

### Reliability and security

- External requests use timeouts, a single retry with backoff, and graceful partial results (section 6).
- Never label sample data as live.
- Keep provider settings on the server and validate all input.
- Use HTTPS.
- Restrict access to saved fields.
- Keep exact coordinates out of storage, URLs and logs.
- Offer deletion if accounts are introduced.

For weak connectivity:

- cache the app shell
- allow a saved report to be viewed offline, with its age and source visible
- give every chart a text alternative

## 10. Suggested build structure and stack

~~~text
field-shift/
  frontend/src/pages/
  frontend/src/components/
  frontend/src/api/
  backend/app/api/
  backend/app/domain/fields.py
  backend/app/domain/plans.py
  backend/app/domain/rules.py
  backend/app/domain/evaluation.py
  backend/app/services/climate_provider.py
  backend/app/services/validation.py
  backend/app/services/site_check.py
  backend/app/services/indicators.py
  backend/app/services/explanations.py
  backend/tests/test_indicators.py        # reproduces the section 17 pilot values
  backend/tests/test_rules.py             # reproduces the section 18 expected results
  data/demo/power_pilot_19911001_20260531.json
  data/demo/sample_case.json
  data/demo/site_check.json
  data/agronomy/crops.json
  data/agronomy/rules.json
  docs/product-spec.md
  docs/data-dictionary.md
  docs/rule-sources.md
~~~

- Use the frontend framework the team knows best.
- Python with FastAPI suits the analysis service if the team knows Python. Use plain Python calculations before adding data libraries.
- SQLite or in-memory storage is enough for a demo. Choose PostgreSQL when deployment and persistence needs justify it.
- Use maps and charts only when they add evidence.

### Minimal API

| Method | Route | Purpose |
|---|---|---|
| POST | /api/v1/analyses | Validate and run a comparison |
| GET | /api/v1/analyses/{id} | Retrieve a saved result |
| GET | /api/v1/crops | List candidate crops and history crop types |
| GET | /api/v1/rules | List rules with citation and review state |
| GET | /api/v1/demo | Provide the clearly labelled sample case |
| GET | /api/v1/health | Deployment health check |

| HTTP status | Body | Meaning |
|---|---|---|
| 200 | `status` = `complete` or `partial` | The analysis ran |
| 422 | `error.code` = `invalid_input`, with per-field messages | Inputs failed section 6.3 |
| 502 | `error.code` = `provider_error` or `no_data`, with `sample_available: true` | Climate data could not be obtained or used |

Request example. This is the demo case in live mode; `extra_candidates` is used only by the sample case.

~~~json
{
  "mode": "live",
  "field": {
    "label": "Sample field",
    "lat": 31.5,
    "lon": 35.1,
    "area": { "value": 20, "unit": "dunum" },
    "irrigation": "rain-fed",
    "soil": "unknown"
  },
  "history": [
    { "season": "2023/24", "crop": "unknown" },
    { "season": "2024/25", "crop": "wheat" },
    { "season": "2025/26", "crop": "wheat" }
  ],
  "candidate_season": "2026/27",
  "goal": "improve_soil_rotation",
  "extra_candidates": []
}
~~~

Response example, shortened to one plan:

~~~json
{
  "analysis_id": "a9f3c2e7",
  "status": "partial",
  "mode": "live",
  "versions": { "rules": "0.1-draft", "engine": "1.0.0", "adapter": "1.0.0", "power_api": "v2.10.3" },
  "data": {
    "provider": "NASA POWER", "parameter": "PRECTOTCORR", "units": "mm/day",
    "period": ["1991-10-01", "2026-05-31"], "valid_days": 12662, "missing_days": 0,
    "retrieved_utc": "2026-11-14T10:00:00Z",
    "site_check": { "result": "not_representative", "cell_mm": 229.4, "station_mm": 470.8, "ratio": 0.49 }
  },
  "plans": [
    {
      "id": "A", "type": "current_practice", "crop": "wheat", "display": "wheat → wheat",
      "why_included": "Current practice: repeats the crop recorded for 2025/26.",
      "status": "evaluated",
      "criteria": [
        { "criterion": "rotation_soil", "label": "concern", "rule": "R1", "rule_state": "draft-unreviewed" },
        { "criterion": "water_fit", "label": "insufficient_evidence", "rule": "R5", "reason": "site_check_failed" },
        { "criterion": "risk", "label": "mixed", "rule": "R6", "value": 34.5, "units": "%" }
      ],
      "inputs": [
        { "name": "crop 2023/24", "state": "missing", "effect": "Not needed: 2024/25 and 2025/26 already confirm a cereal run." }
      ]
    }
  ],
  "limitations": ["Gridded rainfall is regional context, not a field measurement."]
}
~~~

The response has no overall confidence score. The values shown come from the live record retrieved on 14 November 2026 (sections 16–18), except `analysis_id` and `retrieved_utc`, which are placeholders.

## 11. Acceptance criteria

The MVP is ready to demonstrate when all of these hold:

1. The full flow works on phone-sized and desktop screens.
2. At least three plans, including current practice, are compared.
3. Each plan shows why it is included, its benefits and concerns, the evidence, the information gaps, and the risks to review locally.
4. Unknown history and missing climate values stay explicit.
5. Live and sample data are visibly distinct.
6. Every indicator shows its units, period and valid-day count.
7. Every label links to a defined calculation or a rule, and shows that rule's review state.
8. Rejected plans show a plain-language reason (demonstrated with Plan D).
9. The site-check result is shown. Water fit is not computed from absolute rainfall unless the check passes.
10. Changing any input creates a new, reproducible result.
11. Provider errors keep the user's form and do not crash the UI.
12. Every state in section 6.2 can be reached and has its screen state.
13. Each plan's "What we know" panel labels decision-relevant inputs as entered, estimated, assumed or missing, names the source or default, and explains the effect. No overall confidence score is shown.
14. The NASA POWER acknowledgement and data reference appear on the evidence screen and in the printed report.
15. The automated tests reproduce the pilot values in section 17 and the expected results in section 18.
16. The team can state which parts are implemented, simulated or planned (section 19).

Before any real-world recommendation:

- a domain reviewer must check the local crop rules
- the data lead must verify the source product, units, coverage, resolution and station reference
- pilot users should review whether they understand the output

Do not claim field validation without doing it.

## 12. Short build plan

**Align:** confirm the decisions in section 14, especially decision 10. Sketch the comparison UI first.

**Build in order:**

1. Save the pilot POWER record and the sample case as fixtures. Write the indicator and rule tests from sections 17 and 18.
2. Build the UI journey with clearly labelled mock data.
3. Agree the shared data models and the API contract (section 10).
4. Build the climate adapter, validation, provenance, site check, cache and fallback.
5. Build the constraint checks and the evidence-linked evaluation engine.
6. Connect the UI and implement every state in section 6.2.
7. Polish for mobile, add the print view, and check accessibility.
8. Rehearse both paths: live data and unavailable data.
9. Complete the submission checklist (section 21) before the deadline.

Assign owners for data, agronomy, backend, UI, and integration and presentation. Every agricultural rule and data claim needs a reviewer.

## 13. Demo narrative

Show one coherent story:

1. A farmer near Hebron has grown wheat in 2024/25 and 2025/26, and does not remember 2023/24.
2. They enter what they know and mark 2023/24 as unknown.
3. The app retrieves NASA POWER rainfall for the area.
4. **The site check:** the app shows that the NASA grid cell averages about 229 mm per season, while the Hebron station recorded about 471 mm for roughly the same years. It therefore refuses to judge water fit from that number.
5. Three plans are compared:
   - wheat again is a rotation concern
   - lentil and vetch are rotation-favorable
   - all carry the "illustrative rules, not reviewed" label
6. "Why?" reveals rule R1 and the unknown 2023/24 season. That season is not needed, because the two later seasons already confirm the cereal run.
7. The user switches the goal to "conserve water". The criterion order and the summary change; no label changes.
8. The app prints a one-page decision brief with local questions.

The "wow" is trustworthy clarity: people can see why options differ, and where NASA data does and does not fit their place. Avoid claims such as "AI predicts the best crop" or "guaranteed water savings".

## 14. Decisions — proposed answers

Each row is a proposal. The owner confirms or changes it before coding starts.

| # | Decision | Proposed answer | Owner | Status |
|---|---|---|---|---|
| 1 | Pilot location and precision | One representative rain-fed field near Hebron. Coordinates are rounded to 0.1° everywhere: storage, URLs, logs and report. The pilot point is 31.5 N, 35.1 E. Hebron itself is at about 31.53 N, 35.10 E. The live call showed that both fall in the same NASA POWER cell, which spans 31.25–31.75 N and 34.6875–35.3125 E, so rounding does not change the data used. | Data | Proposed; cell boundary verified |
| 2 | Crops and plans | Three plans, each a next-season crop evaluated against the same recorded history: (A) wheat → wheat, current practice; (B) wheat → lentil; (C) wheat → vetch. The sample case adds (D) maize, rejected by H1. The left crop is history context, not an extra planned season. If the immediately preceding season is unknown, the user picks the crop for Plan A. No local reviewer is confirmed yet, so every rule ships as `draft-unreviewed` and the UI shows that label. | Agronomy | Needs reviewer |
| 3 | NASA POWER details | Daily point API, parameter `PRECTOTCORR`, community `AG`, mm/day. See section 16. | Data | Verified by live call, 14 Nov 2026 |
| 4 | Minimum history | Each candidate is evaluated against the seasons immediately before it. R1 needs at most the two preceding seasons; R2 needs the immediately preceding season. A season that was not entered counts as unknown. An unknown that prevents a decision gives "insufficient evidence", never a guess (section 18 flowchart). | Agronomy | Proposed |
| 5 | Ratings | Ordinal only: favorable, mixed, concern, insufficient evidence (meanings in section 7). No 0–100 score in the MVP. The goal changes the criterion order and the summary, never a label. | Backend | Proposed |
| 6 | Language | One UI language for the demo: Arabic if the right-to-left layout is complete by the integration checkpoint, otherwise English. No half-translated selector. Submission text and slides are in English. | UI | Proposed |
| 7 | Persistence | Session only, no accounts. Analysis snapshots are stored in SQLite, keyed by a random analysis ID. The form draft is kept in browser local storage. | Backend | Proposed |
| 8 | Deployment and test device | A static frontend host plus one small FastAPI instance. Warm the cache for the pilot cell at deploy time. Test on one mid-range Android phone in Chrome and one desktop browser. | Integration | Proposed |
| 9 | Generative AI ("SI") | None in the product MVP. Explanations come from deterministic templates filled from engine output. A paraphrasing layer is later work. Any SI tools used to build the project must be disclosed on the submission (section 21). | Backend | Proposed |
| 10 | Grid-cell bias at the pilot | The POWER cell gets about 49% of the rainfall recorded at Hebron station (section 16.1). Proposal: (a) for the MVP, keep POWER and turn off absolute water fit through the site check, so water fit shows "insufficient evidence" with the reason. (b) Stretch goal: add GPM IMERG monthly rainfall at 0.1° (needs a free Earthdata login) and re-run the site check against the station. Promote it only if it passes. (c) Moving the pilot to a site the cell represents is possible, but it loses the prepared demo story. | Data | **Needs team decision** |
| 11 | Station reference | The Hebron station value now comes from a secondary source: Palestinian Meteorological Department monthly means for 2007–2018, as reproduced on Wikipedia. Obtain the primary PMD record or another citable station normal, and record it in `docs/rule-sources.md`. | Data | To do |

### In-app notice

"Field Shift compares options using the information and sources shown. Gridded climate data may not represent conditions within your exact field, and historical conditions do not predict next season. Review choices with local agricultural expertise."

## 15. Final MVP definition

The MVP is a responsive web app, installable as a PWA. It takes one field, its known crop history and a selected goal, and adds historical NASA POWER rainfall context checked against a local station record. It compares at least three plans, including current practice, using a small rule set that is labelled until it is reviewed locally. For each plan it shows, in plain language, why it is included, its evidence, benefits, trade-offs, gaps and uncertainty.

Additional data sources, advanced AI, pest reporting, predictive models and native apps are future work. They depend on validation and on user need.

## 16. Data dictionary — climate source

"Verified" means checked by a live call on 14 November 2026. "Documented" means read on the official POWER documentation pages that day.

| Item | Value | Status |
|---|---|---|
| Provider | NASA POWER (Prediction Of Worldwide Energy Resources) project, NASA Langley Research Center | Documented |
| API | POWER Daily API, version `v2.10.3` (from `header.api.version`) | Verified |
| Endpoint | `https://power.larc.nasa.gov/api/temporal/daily/point` | Verified |
| Query parameters | `parameters=PRECTOTCORR&community=AG&latitude=31.5&longitude=35.1&start=19911001&end=20260531&format=JSON` | Verified |
| Parameter | `PRECTOTCORR`, long name "Precipitation Corrected". The header lists its sources as `MERRA2` and `POWER`. MERRA-2 is a NASA reanalysis: a weather model constrained by many observations. It is not a direct satellite or rain-gauge measurement. The data lead records the correction method from the POWER Methodology pages. | Verified (name, sources); method to record |
| Units | mm/day (`parameters.PRECTOTCORR.units`) | Verified |
| Response path | `properties.parameter.PRECTOTCORR`, a map from `YYYYMMDD` to value | Verified |
| Fill value | `header.fill_value` = `-999.0`. Read it from each response; treat it as missing, never as rain | Verified |
| Time standard | `header.time_standard` = `LST` (local solar time); daily values run from local solar midnight to midnight | Verified |
| Grid | Native cell, no interpolation. Points anywhere within 31.25–31.75 N and 34.6875–35.3125 E return identical values. Neighbouring cells differ. This matches a 0.5° × 0.625° grid. | Verified by probing cell boundaries |
| Cell elevation | `geometry.coordinates[2]` = 342.96 m for the pilot cell | Verified |
| API key | None required | Verified |
| Period requested | 1 Oct 1991 to 31 May 2026: the 30 baseline seasons plus 5 recent seasons. 12,662 daily values returned, 0 missing | Verified |
| Response time | 2.3–2.8 s for `PRECTOTCORR` alone over the full period; 10.9 s for three parameters | Measured once; not a guarantee |
| Errors | HTTP 422 (validation error) and HTTP 429 (too many requests) are documented. No numeric rate limit is published on the API overview page. Cache every response | Documented |

**Resolution warning for the UI:** one grid cell is about 56 km × 59 km at this latitude. It spans the Hebron hills (about 930 m), the lower land around them, and areas east towards the Dead Sea. That is why its mean elevation is 343 m. The app reports the cell value as regional context and says so on the evidence screen.

**Acknowledgement, from the POWER Referencing Guide, for the report, evidence screen and slides:**

> The data was obtained from National Aeronautics and Space Administration (NASA) Langley Research Center's Prediction Of Worldwide Energy Resources (POWER) project funded through the NASA Earth Science Division.

**Data reference.** The app fills in the version and access date from the provenance record:

> The data was obtained from the POWER Project's Daily 2.10.3 version on 2026/11/14.

POWER also asks users to send a reference or a short description of any published use to larc-power-project@mail.nasa.gov. This is optional and is the team's choice.

**Provenance record stored with each dataset:**

- provider, API version, parameter, community
- rounded latitude and longitude, cell elevation
- requested start and end dates, actual first and last dates returned
- count of valid days, count of missing days
- units, time standard
- retrieval timestamp (UTC)
- site-check result
- adapter version

### 16.1 Site check — does the grid cell represent the field?

A NASA POWER cell averages over about 3,300 km². Absolute rainfall from the cell may be far from what falls on the field. The site check compares the cell with a local station record over roughly the same period, before any absolute-rainfall rule (R4) is allowed to run.

| Step | Rule |
|---|---|
| Inputs | A station mean Oct–May rainfall, with its source and period. The cell's mean Oct–May total over the matching seasons |
| Ratio | r = cell mean ÷ station mean |
| Representative | 0.80 ≤ r ≤ 1.25. R4 may run |
| Not representative | r < 0.80 or r > 1.25. R4 is replaced by R5 (insufficient evidence), with the reason shown |
| Not checked | No station record. R4 is replaced by R5, with "absolute rainfall not checked against a local record" |

The 0.80–1.25 band is a team choice made so the result is reproducible. It is not a scientific standard, and the evidence screen says so.

**Pilot result, computed 14 November 2026:**

| Quantity | Value | Source |
|---|---|---|
| Hebron station, mean Oct–May rainfall | 470.8 mm: the sum of monthly means for Oct–May, 2007–2018 | Palestinian Meteorological Department, as reproduced on Wikipedia "Hebron"; primary source to obtain (decision 11) |
| POWER cell, mean Oct–May total, 2007/08–2017/18 | 229.4 mm | Live POWER record |
| Ratio r | 0.49 | Not representative |
| Elevation | Cell 343 m; Hebron about 930 m | POWER response; Wikipedia "Hebron" |

Without this check, R4 would label wheat a "concern" at Hebron, because only 1 of 30 baseline seasons in the cell reached 450 mm. That result would come from the cell's dryness, not from the field.

Relative indicators are still shown as regional context, with a caveat. These are the anomalies, the variability (CV) and the recent shift. R6 still runs. Drier cells tend to show higher variability, so the cell's CV may overstate variability at the field. The agronomy and data owners confirm this treatment.

## 17. Indicator definitions

**Season:** 1 October of year Y to 31 May of year Y+1, labelled Y/Y+1. That is 243 days, or 244 when February has 29 days. This is the team's working definition of the rain-fed winter season; the agronomy owner confirms it.

**Baseline:** the 30 seasons 1991/92 to 2020/21. **Recent seasons:** the 5 seasons 2021/22 to 2025/26.

**Valid season:** at least 95% of its days have valid values. That is at least 231 days, or 232 in a 244-day season.

| ID | Indicator | Formula | Units | Minimum coverage | If not met |
|---|---|---|---|---|---|
| I1 | Seasonal rainfall total | Sum of daily `PRECTOTCORR` over the season | mm | Valid season | Season marked unavailable and excluded |
| I2 | Baseline mean | Mean of the valid baseline seasonal totals | mm | At least 24 of 30 baseline seasons valid | Unavailable |
| I3 | Season anomaly | (season total − baseline mean) ÷ baseline mean × 100, shown for each recent season | % | That season and the baseline both valid | Unavailable for that season |
| I4 | Variability (CV) | Sample standard deviation (n − 1) of the valid baseline totals ÷ baseline mean × 100 | % | Same as I2 | Unavailable |
| I5 | Seasons meeting a threshold | Count of valid baseline seasons with total ≥ threshold T, shown as "n of N" | count | Same as I2 | Unavailable |
| I6 | Recent shift | (mean of valid recent totals − baseline mean) ÷ baseline mean × 100. Context only; no rule uses it | % | At least 4 of 5 recent seasons valid, and I2 available | Unavailable |

**Rules for all indicators:**

- Missing days are excluded from sums and counted separately.
- The valid-day count is shown beside every total.
- Every value is labelled "historical", never "expected" or "forecast".
- I6 is labelled "five seasons are too few to establish a trend".

**Pilot values.** These come from the live record retrieved on 14 November 2026, for the regional cell, which is not the field. They are test fixtures: `test_indicators.py` must reproduce them from the saved record.

| Indicator | Value |
|---|---|
| Valid seasons | 35 of 35 (no missing days) |
| I2 baseline mean | 225.2 mm |
| I4 CV | 34.5% (sample SD 77.8 mm) |
| I5 seasons ≥ 450 mm | 1 of 30 (2019/20, 491 mm) |
| I1 recent totals | 2021/22: 407 mm; 2022/23: 331 mm; 2023/24: 350 mm; 2024/25: 143 mm; 2025/26: 328 mm |
| I3 recent anomalies | 2021/22: +80.8%; 2022/23: +46.9%; 2023/24: +55.2%; 2024/25: −36.6%; 2025/26: +45.6% |
| I6 recent shift | +38.4% |

## 18. Draft rule set (version 0.1, `draft-unreviewed`)

**No agricultural specialist has reviewed anything in this section.** The citations name where support should be found. Before a rule's status changes, the agronomy owner must find the exact document and page and record it in `docs/rule-sources.md`. Until then, the comparison screen shows a visible "illustrative rules, not reviewed" label.

### Rule review lifecycle

~~~mermaid
stateDiagram-v2
  state "draft-unreviewed" as Draft
  state "reviewed" as Reviewed
  state "retired" as Retired
  [*] --> Draft : rule written, citation to locate
  Draft --> Reviewed : reviewer confirms condition, effect, scope and citation
  Draft --> Retired : reviewer rejects
  Reviewed --> Draft : condition, effect or scope edited (new version)
  Reviewed --> Retired : superseded or withdrawn
  Retired --> [*]
~~~

During the demo, `draft-unreviewed` rules apply, and every result they produce carries the label. Beyond the demo, only `reviewed` rules apply.

### Candidate crop profiles

| Crop | Type | Season | Indicative crop water need (whole growing period) | Source |
|---|---|---|---|---|
| Wheat | Cereal | Winter, rain-fed | 450–650 mm | FAO, *Irrigation Water Management* Training Manual No. 3, section 3.3.4, Table 14 ("Barley/Oats/Wheat 450–650", drought sensitivity low–medium). Verified at fao.org/4/s2022e/s2022e07.htm on 14 Nov 2026 |
| Lentil | Grain legume | Winter, rain-fed | No confirmed figure. Table 14 has no lentil entry; it lists pea at 350–500 mm. Whether that applies to lentil is a question for the reviewer | ICARDA or FAO, to locate |
| Vetch | Forage legume | Winter, rain-fed | No confirmed figure | ICARDA forage legume publications, to locate |

FAO describes Table 14 values as rough estimates of crop evapotranspiration, for use when they cannot be calculated more accurately. They describe the crop's full water need, not the minimum rainfall for a viable rain-fed crop. A crop with no confirmed figure gets "insufficient evidence" for water fit; it does not inherit another crop's number.

### History crop list

History entries need only a crop type. That is why this list is wider than the candidate list.

| Choice | Type used by R1 and R2 |
|---|---|
| Wheat, barley | Cereal |
| Lentil, chickpea | Legume (grain) |
| Vetch | Legume (forage) |
| Fallow | Non-cereal, non-legume |
| Other crop | Type unknown; treated as unknown |
| Unknown, or season not entered | Unknown |

### Hard constraints

The engine checks these first. A failure rejects the plan with the reason shown.

| ID | Condition | Rejection reason shown |
|---|---|---|
| H1 | The candidate crop is not in the supported candidate list (wheat, lentil, vetch) | "This crop is not supported in this version." |
| H2 | The candidate's profile season does not match the candidate season (winter 2026/27) | "This crop is not grown in the selected season in this version." |
| H3 | The candidate is marked irrigated-only and the field is recorded as rain-fed | "This crop needs irrigation; the field is recorded as rain-fed." |

None of the three MVP crops trips H2 or H3. Those checks exist so the rule set is ready for more crops. The rejection path is shown with Plan D (maize, sample case only), which fails H1.

### Criterion rules

All plans are next-season candidates appended to the recorded history. "Previous season" means the immediately preceding season in that history. Never skip an unknown season to reach an older crop. For display, `wheat → lentil` means wheat was recorded in the immediately preceding season and lentil is the next-season candidate. If that season is unknown, display `unknown → lentil`.

| ID | Criterion | Condition | Result | Rationale to confirm | History needed |
|---|---|---|---|---|---|
| R1 | Rotation/soil | The candidate is a cereal, and the two immediately preceding seasons are both cereals, which would make 3 or more consecutive cereal seasons | Concern | Continuous cereal is associated with a build-up of cereal diseases and weeds, and with drawing down soil nitrogen | The 2 immediately preceding seasons. A known non-cereal breaks the run. An unknown that leaves the run unconfirmed and unbroken gives insufficient evidence |
| R2 | Rotation/soil | The candidate is a legume (grain or forage) and the immediately preceding season was a cereal | Favorable | Legumes fix nitrogen and interrupt cereal disease cycles | Immediately preceding season known |
| R3 | Rotation/soil | Neither R1 nor R2 applies, and the history is enough to rule both out | Mixed | No specific rotation effect identified | As in the flowchart below |
| R4 | Water fit | All of: the site check is "representative"; irrigation is rain-fed; the crop has a confirmed lower water bound T; I5 is available. Share of valid baseline seasons with total ≥ T: 80% or more is favorable; 50% to under 80% is mixed; under 50% is concern | As computed | Compares historical seasonal rainfall with the crop's indicative need. This is a simplification: not all rainfall reaches the crop (runoff, evaporation, soil storage), and T is the full water need. The reviewer confirms whether the lower FAO bound suits a rain-fed comparison | None (uses climate data) |
| R5 | Water fit | Any condition of R4 is not met: no confirmed water figure; irrigation is irrigated, mixed or unknown; baseline unavailable; site check "not representative" or "not checked" | Insufficient evidence, with the specific reason | Irrigated and mixed fields get water from sources the MVP does not measure | — |
| R6 | Risk | Baseline CV (I4): under 20% is favorable; 20% to 35% inclusive is mixed; over 35% is concern. Every plan at one location gets the same label: it describes the area, not the crop | As computed | Higher year-to-year rainfall variability means a less dependable season. Regional value (section 16.1) | None |

The 80/50 and 20/35 cut-offs are team choices made so labels are reproducible. They are not agronomic standards, and the evidence screen says so.

The current-practice plan repeats only a crop recorded in the immediately preceding season. Otherwise the user picks the Plan A crop.

### Rotation/soil decision flowchart (R1–R3)

This is the exact logic `rules.py` implements for each plan. "Unknown" includes "other crop" and seasons that were not entered.

~~~mermaid
flowchart TD
  S(["Candidate crop and recorded history"]) --> C{"Candidate type?"}
  C -->|"Cereal"| P1{"Previous season type?"}
  P1 -->|"Unknown"| IE1["Insufficient evidence: previous season unknown"]
  P1 -->|"Legume or fallow"| M1["Mixed (R3): run of cereals broken"]
  P1 -->|"Cereal"| P2{"Season before that?"}
  P2 -->|"Unknown"| IE2["Insufficient evidence: cannot confirm or rule out a third cereal season"]
  P2 -->|"Legume or fallow"| M2["Mixed (R3): only 2 cereal seasons in a row"]
  P2 -->|"Cereal"| CON["Concern (R1): at least 3 cereal seasons in a row"]
  C -->|"Legume"| Q1{"Previous season type?"}
  Q1 -->|"Unknown"| IE3["Insufficient evidence: previous season unknown"]
  Q1 -->|"Cereal"| FAV["Favorable (R2): legume after cereal"]
  Q1 -->|"Legume or fallow"| M3["Mixed (R3): no specific rotation effect"]
~~~

### Expected results for the demo case

This table is the test fixture for `test_rules.py`. The inputs are: history 2023/24 unknown, 2024/25 wheat, 2025/26 wheat; candidate season 2026/27; rain-fed; site check not representative (r = 0.49); CV 34.5%.

| Plan | Rotation/soil | Water fit | Risk | Notes |
|---|---|---|---|---|
| A wheat → wheat (current practice) | Concern (R1) | Insufficient evidence (R5: site check) | Mixed (R6) | 2023/24 unknown is not needed |
| B wheat → lentil | Favorable (R2) | Insufficient evidence (R5: no confirmed figure; site check) | Mixed (R6) | |
| C wheat → vetch | Favorable (R2) | Insufficient evidence (R5: no confirmed figure; site check) | Mixed (R6) | |
| D maize (sample case only) | — | — | — | Rejected by H1 |

With goal "improve soil and rotation", the summary reads: "Rotation/soil differs: wheat again is a concern, while lentil and vetch are favorable. Water fit could not be assessed for any plan." Risk is the same for every plan, so the summary does not mention it.

### Local questions printed on every report

- Is rainfall at your field closer to the Hebron station record or to the regional value shown?
- Is there a buyer or a use for lentil or vetch near you, and at what price?
- Are seed and suitable harvesting equipment available for the alternative crop?
- What has your agricultural extension officer seen with these rotations locally?

### Explanation templates

In these templates:

- `{season1}` is the immediately preceding season, and `{prevCrop}` is its crop.
- `{season2}` is the season before `{season1}`.
- `{cell}` and `{station}` are the site-check means (16.1).

- **Rotation concern (R1):** "This plan would make at least 3 cereal seasons in a row on this field ({season2}, {season1}, and next season). Draft rule R1 flags this as a rotation concern. Rule status: not yet reviewed."
- **Rotation benefit (R2):** "{crop} is a legume following a cereal ({season1}: {prevCrop}). Draft rule R2 marks this as a rotation benefit. Rule status: not yet reviewed."
- **Rotation mixed (R3):** "No specific rotation effect was identified for {crop} after {prevCrop}. Rule status: not yet reviewed."
- **Water fit (R4):** "In {n} of {N} past seasons ({first}–{last}), rainfall for this area reached {T} mm, the lower FAO indicative water need for {crop}. Area data comes from one NASA POWER grid cell and was checked against {station}."
- **Water fit, site check failed (R5):** "We could not assess water fit, because the NASA POWER area average ({cell} mm per season) differs too much from the local station record ({station} mm). This is not a negative result."
- **Variability (R6):** "Rainfall in this area varied by {cv}% from season to season ({first}–{last}). Team cut-offs: under 20% favorable, 20–35% mixed, over 35% concern. This describes the area, not the crop."
- **Insufficient (general):** "We could not assess {criterion} for this plan, because {reason}. This is not a negative result."

## 19. Implemented, simulated, planned

Keep this table current during the build. It answers acceptance criterion 16 and goes on the last slide.

| Part | State at start of build | Target for demo |
|---|---|---|
| UI journey, all nine screens | Planned | Implemented |
| NASA POWER adapter, validation, provenance | Planned (API details verified) | Implemented, with cached pilot record and sample fallback |
| Site check (16.1) | Planned (pilot values computed) | Implemented |
| Indicators (section 17) | Planned (pilot values computed) | Implemented, with tests |
| Rule engine (section 18) | Planned | Implemented, with tests |
| Rule content | Draft, unreviewed | Simulated: labelled illustrative unless a reviewer signs off |
| Station reference value | Secondary source | Primary source, if obtained (decision 11) |
| Lentil and vetch water figures | Missing | Shown as insufficient evidence unless sourced |
| GPM IMERG rainfall | Not started | Stretch goal (decision 10b); otherwise stated as planned |
| Print report | Planned | Implemented through browser printing |
| Offline saved report, PWA install | Planned | Implemented if time allows; otherwise stated as planned |
| Arabic interface | Planned | Per decision 6 |
| Field validation with farmers | Not done | Not done; stated plainly |

## 20. Challenge coverage

This table maps each item on the challenge page to the spec. "May" items in the challenge are optional; the table says what Field Shift does about each.

| Challenge item | Field Shift | Status |
|---|---|---|
| Decision-support tool using NASA Earth observations | NASA POWER `PRECTOTCORR` drives the indicators, the site check and R6, and gates R4. NASA data is core, not decoration, which is what the judging Relevance criterion asks for | MVP |
| Local soil information | Optional soil-type input, shown as context; no MVP rule uses it. Web Soil Survey and SSURGO are U.S.-only and do not cover Hebron. FAO GAEZ is global and a later candidate | Partial |
| Crop characteristics | Crop profiles and types (section 18) | MVP |
| Farmer priorities | Goal selection (section 7); irrigation type. Market and equipment are covered by the local questions now and are later inputs | MVP, partial |
| Compare at least three rotation strategies, including the existing one | Plans A (current practice), B and C | MVP |
| For each strategy: why suggested, evidence, benefits, gaps, risks for local review | The five per-plan questions in section 7 | MVP |
| Rainfall patterns and long-term water trends | I1–I6, including the recent shift (I6) | MVP |
| Satellite and model data compared with ground measurements | Site check against the Hebron station (16.1); shown on the evidence screen | MVP |
| Explain scientific terms | Evidence screen and glossary (section 22) | MVP |
| Reminder that the tool supports, not replaces, local expertise | In-app notice, local questions, draft-rule label | MVP |
| Temperature, heat stress, frost risk | `T2M_MAX` and `T2M_MIN` are available from the same API (verified 14 Nov 2026). Not in the MVP: the cell is about 590 m lower than Hebron, so raw values run warm. This needs an elevation adjustment (SRTM plus a lapse rate) and reviewed crop thresholds | Later |
| Higher-resolution rainfall (GPM IMERG) | Candidate fix for the grid-cell bias (decision 10b) | Stretch or later |
| Soil moisture (SMAP), evapotranspiration (ECOSTRESS) | Needs work on resolution, coverage and access first. OpenET is western-U.S. only | Later |
| Bare-field periods and vegetation stress (Landsat, MODIS/VIIRS, Sentinel-2 NDVI) | Needs field boundaries and processing time | Later |
| Erosion and slope (SRTM) | Needs a field polygon and an erosion rule | Later |
| Groundwater trends (GRACE/GRACE-FO) | Resolution of a few hundred km; cannot inform one field | Not planned |
| AI ("SI") or statistical pattern finding | Transparent statistics (means, anomalies, CV, threshold counts). No machine learning in the MVP, because 30 seasons in one cell are too few to train or validate a model honestly | MVP (statistics only) |
| Harmonizing datasets to a common grid | Not needed with one source; required if IMERG is added | Later |
| Interactive maps, scenario sliders | The map is used only to pick a location | Not in MVP |

Of the Resources-tab datasets, several are U.S.-only or North America-only and cannot serve a Hebron pilot. These are Web Soil Survey, SSURGO/STATSGO2, CDL, PRISM, NAIP, NLCD, CoCoRaHS, NWIS, NLDAS, USDA AMS, NASS QuickStats, OpenET and LANDFIRE. The global options are SMAP, GPM IMERG, Landsat, MODIS/VIIRS, NASA POWER, SRTM, ECOSTRESS, GEDI, GLDAS, FAO GAEZ, Sentinel-2 and ERA5.

## 21. Submission checklist

Based on the Space Apps 2026 Project Submission Guide and Judging & Awards Guide, read on 14 November 2026.

- [ ] **Deadline:** submit through the team's project page before Sunday 15 November 2026, 23:59, Local Event time. Universal Event teams use the Team Owner's local time.
- [ ] **Team:** at most 6 members. Universal Event teams need at least 2 to be eligible for global judging.
- [ ] **Project name** and **high-level summary:** what it does, how it addresses the challenge, and why it matters.
- [ ] **Project demo:** either a 7-slide presentation (including the title and introduction slides) or a video of 30 seconds or less. Use a public link that needs no login.
- [ ] **Final project link:** public, with no login. For example, the deployed app plus a public repository.
- [ ] **Detailed description:** what it does, how it works, benefits, goals, and the tools and languages used.
- [ ] **NASA data:** NASA POWER Daily API v2.10.3, `PRECTOTCORR`, community AG, 1 Oct 1991 to 31 May 2026, accessed 14 Nov 2026. At least one NASA dataset is required for global awards.
- [ ] **Other references:** FAO Training Manual No. 3, Table 14; the Hebron station source; all code libraries and any images used.
- [ ] **Use of SI:** describe every SI tool used to build the project, such as coding assistants and chatbots. SI-generated code or data must be acknowledged in descriptive text and metadata. SI-generated images or video need a visible watermark. SI must not be used to come up with the idea for the solution.
- [ ] **No NASA logos or branding** in generated content.
- [ ] **Shown on the demo:** the implemented, simulated and planned table (section 19).

**Judging criteria**, each scored 1–5:

- **Impact:** smallholder decisions under shifting rainfall.
- **Creativity:** a tool that checks its own NASA data against the ground before using it.
- **Validity:** tested, reproducible rules with honest gaps.
- **Relevance:** NASA POWER is central to every climate label.
- **Presentation:** one clear story (section 13).

**Seven-slide outline:**

1. Title
2. The farmer's problem
3. Field Shift and the user flow
4. NASA data and the site check
5. The three-plan comparison
6. Evidence, limits and next data sources
7. Implemented, simulated and planned

## 22. Glossary

| Term | Plain meaning |
|---|---|
| NASA POWER | A NASA service that provides ready-to-use daily weather and climate values for any point on Earth |
| `PRECTOTCORR` | POWER's corrected daily precipitation, in mm per day |
| Reanalysis (MERRA-2) | A reconstruction of past weather made by combining a weather model with many observations. Consistent everywhere, but averaged over large cells |
| Grid cell | The area one value represents. Here about 56 km × 59 km, much larger than a field |
| Site check | A comparison of the grid cell's rainfall with a local weather station, to decide whether absolute amounts can be trusted for this place |
| Local solar time (LST) | Time based on the sun's position at the location; POWER's daily values use it |
| Season | 1 October to 31 May, the rain-fed winter growing season in this spec |
| Baseline | The 30 seasons from 1991/92 to 2020/21, used as "normal" for comparison |
| Anomaly | How much wetter or drier a season was than the baseline, in percent |
| Coefficient of variation (CV) | How much seasonal rainfall usually swings from year to year, as a percentage of the average |
| Crop water need | The water a crop uses over its growing period (evapotranspiration) when it is not short of water. It is not the same as rainfall |
| Evapotranspiration | Water lost from soil by evaporation plus water released by plants |
| Rain-fed | Grown without irrigation, relying on rainfall |
| Legume | A plant such as lentil or vetch that hosts bacteria which fix nitrogen from the air into the soil |
| Cereal run | Consecutive seasons of cereal crops such as wheat or barley on the same field |
| Hard constraint | A rule that rejects a plan outright, such as an unsupported crop |
| Insufficient evidence | The app could not assess a criterion. This is not a negative result |
| Draft-unreviewed | A rule written by the team that no agricultural specialist has checked yet |
| SI | "Super Intelligence", the term Space Apps 2026 uses for what is usually called AI |
