# AstroRoot backend

Current full-app setup and limits: [root README](../README.md) and [full delivery record](../docs/full-app-delivery.md). The public home page is at `/`, the field/account workspace is at `/workspace/`, and methods are at `/science/`.

Python 3.12 + FastAPI.

Backend 2.2.0: see [the backend handoff](../docs/backend-handoff.md) for OpenAI configuration, private API
contracts, point layers, scenarios, source artifacts, deployment and remaining scientific validation gates.

API 2.3.0 adds national NASA imagery, derived COG processing, frozen external evaluation and English/Arabic
evidence responses. See [scientific delivery](../docs/scientific-delivery.md) for live checks, quota/CIMIS
blockers, failed validation gates and the exact national-versus-Kansas coverage distinction.

- **U.S. release** (`/api/v2`, web app at `/`): NASA POWER daily weather, USDA SSURGO soils and FAO-56
  (Penman–Monteith ET0, crop coefficients, daily root-zone water balance) replayed over 25 past seasons for current
  practice and two alternatives. Earlier specifications are in `../docs/archive/`.
- The earlier Hebron prototype (`/api/v1`, `/v1/`) was retired on 2026-11-15.

## Run

From this folder:

```text
python -m venv .venv
.venv\Scripts\activate          (macOS or Linux: source .venv/bin/activate)
pip install -r requirements.txt
pytest
uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000 for the app, or http://127.0.0.1:8000/docs for the API.

Command line, no web app needed:

```text
python -m app.cli --site ks_hays --history maize_grain:2024,maize_grain:2025 --irrigation rain-fed
python -m app.cli --live --lat 41.59 --lon -93.62 --out result.json --report report.md
```

`--site` uses the saved, validated records in `../data/fixtures` (offline). `--live` calls NASA POWER and USDA Soil
Data Access. Set `FIELD_SHIFT_DB` to choose the database
file (default `field_shift.db`). The tests run offline.

## Farmer reports and expert inbox

The workspace offers a print-ready analysis report. Choose **Export full report · Save as PDF**, then choose **Save as PDF** in the browser print dialog. It includes the field profile, crop summaries, relative water-gap scores, season-by-season values, assumptions, source provenance, equations and limitations.

The displayed percentage is a relative water-gap score: each crop's median rain-fed deficit divided by the largest median deficit among the three options. It compares only those crops in that analysis; the separate count shows how often any modeled stress day occurred. Neither is a probability of crop failure, yield or profit. The model remains unvalidated at field level.

Farmer questions are stored in the in-app expert queue and can be answered in `/expert/`. Configure a private, randomly generated `FIELD_SHIFT_EXPERT_KEY` on the server before enabling the expert inbox. The key is never committed to the repository. Farmers see answers in their account under **Expert replies**.

## Layout

- `app/science/` pure equations (FAO-56, water balance, statistics) with an equation register
- `app/adapters/` NASA POWER and SSURGO: fetch, zero-tolerance validation, manifests
- `app/geo/` 50-state boundary check
- `app/services/` source retrieval and caching, the replay engine, report
- `app/api/v2.py` coverage, crops, equations, boundaries, async analysis jobs, results, reports
- `tools/census_states_to_geojson.py` rebuilds `../data/catalogs/us_states_50_cb_2023_20m.geojson`
