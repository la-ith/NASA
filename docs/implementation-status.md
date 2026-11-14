# Implementation status against spec v4.0

As of 14 November 2026. Implemented means built and tested; validated means compared with independent field
observations, which has **not** been done for any output.

| Spec item | State | Evidence |
|---|---|---|
| Phase 1: U.S. forcing record, crop/soil configuration, reference calculations | Done | 2 sites × 25 years of POWER weather; SSURGO soils; FAO-56 Examples 2–35 pass |
| Phase 2: ingestion, provenance, ET0, crop demand, water balance, ≥3 strategies, JSON + report without the web | Done for 3 crops | `app/science`, `app/adapters`, `app/services`; `python -m app.cli`; 120 tests |
| Geography: all 50 states, Alaska antimeridian, Hawaii, outside-scope rejection | Done | `tests/test_geo.py` (15 points) |
| Historical / simulation / prediction distinction | Done | Every output carries `historical_analysis` or `conditional_simulation`; no prediction is offered |
| Phase 3: sampling study, independent evaluation, error metrics | Development pilot started, no nationwide accuracy claim | `validation/pilot-validation-report.md`; 2020–2022 station comparisons, holdouts reserved |
| Phase 4: U.S. web app with MapLibre map, async jobs, coverage, evidence, report | Built | `frontend/` at `/`; checked in a browser for the sample and live flows. Map basemap and outlines, Alaska/Hawaii shortcuts, and forced-style-failure fallback were visually observed on 14 November 2026. Attu (52.93 N, 173.2 E) was accepted through coordinate entry; precise map-click on Attu was not certified |
| Map scientific layers (precipitation, ET0, deficit rasters), layer manifests, tiles | Not started | Map shows state outlines, basemap and the selected point only |
| Phase 5: grounded chatbot | Not started | — |
| Phase 6: Palestine | Not started; Hebron v3 app kept at `/v1/` as regression only | — |
| CDL, IMERG, SMAP, PRISM and other catalog sources | Not integrated | Coverage reports them as `not_integrated` |
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
