# Implementation status against spec v4.0

As of 14 November 2026. Implemented means built and tested; validated means compared with independent field
observations, which has **not** been done for any output.

| Spec item | State | Evidence |
|---|---|---|
| Phase 1: U.S. forcing record, crop/soil configuration, reference calculations | Done | 2 sites × 25 years of POWER weather; SSURGO soils; FAO-56 Examples 2–35 pass |
| Phase 2: ingestion, provenance, ET0, crop demand, water balance, ≥3 strategies, JSON + report without the web | Done for 3 crops | `app/science`, `app/adapters`, `app/services`; `python -m app.cli`; 120 tests |
| Geography: all 50 states, Alaska antimeridian, Hawaii, outside-scope rejection | Done | `tests/test_geo.py` (15 points) |
| Historical / simulation / prediction distinction | Done | Every output carries `historical_analysis` or `conditional_simulation`; no prediction is offered |
| Phase 3: sampling study, independent evaluation, error metrics | **Not started** | No accuracy claims are made |
| Phase 4: U.S. web app with MapLibre map, async jobs, coverage, evidence, report | Built | `frontend/` at `/`; checked in a browser for the sample and live flows. The map's tile rendering could not be checked visually in the test browser (it was not drawing frames); the outlines-only fallback is in place |
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
