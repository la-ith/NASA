# Field Shift project evidence

Status snapshot: 15 November 2026. This index separates implementation checks from evidence of real-world accuracy. The project is an independent research prototype; the evidence below does not qualify it for farm prescriptions.

## What the evidence supports

| Judging question | Demonstrable evidence | What it does not prove |
|---|---|---|
| Impact | A farmer can save a field, add their own context, compare three modeled crop options, keep notes, request an agronomist response, and export a report. See [full application delivery](full-app-delivery.md). | Farmer outcomes, adoption, yield gains, income, water savings, agronomist response capacity, and improved decisions have not been measured in a field pilot. |
| Creativity | NASA POWER weather drives FAO-56 reference evapotranspiration and the crop water-balance replay; USDA SSURGO provides mapped soil inputs. National 2020 scenario artifacts were processed for all three crops. | NASA imagery is not used as numerical input by reading its colours. SMAP imagery is contextual only; direct numerical SMAP ingestion is not established. A map pin and coarse grid do not represent a surveyed field. |
| Validity | FAO worked-example checks, water-balance closure checks, automated tests, preserved source hashes, and a frozen external weather-screening protocol are available. | Frozen screening returned **not qualified**: 4 of 21 station-seasons passed all provisional gates; among 18 eligible seasons after excluding the diagnostic-only Fort Collins station, 4 passed and 14 failed. Crop irrigation accuracy and agronomist review remain unverified. |
| Relevance | The calculation uses NASA data in its core weather-demand calculation, and USDA soil data in its soil-water assumptions. Equations, source selection, units, spatial support, and limitations are documented. | National completion is not proof of nationwide suitability. The 2020 map is one scenario, and valid-pixel coverage differs by crop and metric. |
| Presentation | The public home, field workspace, methods page, saved Hays example, map layers, and print-to-PDF report support a judge walkthrough. | No independent usability study or accessibility audit is claimed. Use the current UI as a demo, not as validation evidence. |

## Reproducible checks

Run from the repository root in PowerShell, with dependencies already installed:

```powershell
Set-Location backend
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe tools/verify_national_delivery.py
Set-Location ..
node --test frontend/tests/*.test.mjs
```

The national verifier checks each published raster checksum, canonical publication record hash, COG layout, per-metric valid-cell counts, duplicate/missing grid cells, 50-state coverage, and canonical source JSON hashes. It writes a refreshed integrity report to `docs/validation/results/national-grid-delivery.json`. These checks establish artifact integrity and processing completeness, not scientific accuracy.

For the no-network scientific replay, use the saved Hays fixture:

```powershell
Set-Location backend
.venv/Scripts/python.exe -m app.cli --site ks_hays --history maize_grain:2024,maize_grain:2025 --irrigation rain-fed
Set-Location ..
```

The CLI replay demonstrates the calculation path from stored weather and soil inputs to crop-water outputs. It is not an external validation run. Live analyses retrieve current provider records and should be shown with their own source dates and provenance.

On this verification run, the Hays sample completed all 25 seasons. Median rain-fed deficit was 371.7 mm/season for maize, 415.6 for soybean, and 233.8 for sorghum; median net irrigation requirement was 503.3, 540.5, and 355.6 mm/season, respectively. These are outputs of the example scenario, not measured farm outcomes.

The 15 November verification run passed **194 backend tests** and **4 JavaScript tests**. The national integrity check processed all 3,557 planned US50 grid locations for each of the three crop scenarios and verified canonical source hashes for 3,557 POWER, 3,165 SSURGO, and 3,165 SSURGO-restriction records. The backend run emitted one existing Starlette/AnyIO deprecation warning.

## Evidence files

- [Frozen holdout protocol](../data/catalogs/validation_protocol_v1.json) — criteria and evaluation groups were locked before the reserved data were opened.
- [Holdout summary](validation/holdout-evaluation-v1.md) and [full machine-readable results](validation/results/holdout-evaluation-v1.json) — all groups are consumed and cannot be reused as unseen tests after tuning.
- [Pilot report](validation/pilot-validation-report.md) — development comparisons, QA rules, missingness, time-alignment caveats, and numerical-vs-environmental verification.
- [Fresno CIMIS comparison](validation/fresno-cimis-comparison.md) — independent reference-weather comparison, with its paired-day counts and limitations.
- [National-grid delivery](validation/results/national-grid-delivery.json) — per-crop valid-cell counts and reproducible SHA-256 checks.
- [Equation register](equation-register.md), [data sources](data-sources.md), and [scientific delivery](scientific-delivery.md) — model lineage and validation interpretation.
- Runtime source manifests and raw responses under `data/validation/raw/` — request details, retrieval time, quality handling, and hashes.

## Accuracy, score, and factor language

The displayed percentage is a **relative water-gap score**: a crop's median modeled rain-fed deficit divided by the largest median deficit among the three options. It is not a probability of failure, yield, profit, or forecast. The count of historical seasons with a modeled stress day is a separate measure.

The API/PDF field named `primary_contributing_factor` describes the median modeled deficit as a combined effect of crop demand, past weather, and mapped soil storage. It is not a quantitative attribution that isolates which input caused the deficit. At this source snapshot, the strategy cards do not render that API field. Avoid presenting the combined description as a proven dominant cause; if the interface adds it, label it as a modeled combined driver and explain its scope.

## Evidence still needed before stronger claims

1. **Fresh independent evaluation:** preregister outputs, sampling, QA, and acceptance gates before collecting any new comparison data. The evaluated holdouts are consumed; do not tune on them and relabel them as fresh evidence.
2. **Field-level crop-water validation:** collect observed irrigation, soil moisture, crop stage, and preferably crop ET or stress observations, with management and application-efficiency context. Include multiple climates, soil types, and irrigation practices.
3. **Agronomist review:** have qualified reviewers assess crop parameters, calendars, soil assumptions, and farmer-facing guidance; record reviewer scope and dispositions.
4. **Farmer usability and impact:** test task completion and comprehension with farmers. Ask whether they understand the historical-versus-forecast distinction, score meaning, uncertainty, and when to seek local advice.
5. **Operational proof:** verify actual PDF output, expert-queue response workflow, and deployment on the target host before claiming these are production services.

Until these are complete, describe Field Shift as a transparent historical research comparison that helps prepare questions for local experts, not as a validated crop-selection or irrigation recommendation system.
