# Field Shift backend

Python 3.12 + FastAPI.

Backend 2.2.0: see [the backend handoff](../docs/backend-handoff.md) for OpenAI configuration, private API
contracts, point layers, scenarios, source artifacts, deployment and remaining scientific validation gates.

API 2.3.0 adds national NASA imagery, derived COG processing, frozen external evaluation and English/Arabic
evidence responses. See [scientific delivery](../docs/scientific-delivery.md) for live checks, quota/CIMIS
blockers, failed validation gates and the exact national-versus-Kansas coverage distinction.

- **v4 U.S. release** (`/api/v2`, web app at `/`): NASA POWER daily weather, USDA SSURGO soils and FAO-56
  (Penman–Monteith ET0, crop coefficients, daily root-zone water balance) replayed over 25 past seasons for current
  practice and two alternatives. See `../Field Shift Product Spec v4_0.md` and `../docs/`.
- **v3.2 Hebron prototype** (`/api/v1`, app at `/v1/`): kept as regression tests only.

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
Data Access. Legacy warmup is off by default; set `FIELD_SHIFT_WARMUP=1` to enable it. Set `FIELD_SHIFT_DB` to choose the database
file (default `field_shift.db`). The tests run offline.

## Layout

- `app/science/` pure equations (FAO-56, water balance, statistics) with an equation register
- `app/adapters/` NASA POWER and SSURGO: fetch, zero-tolerance validation, manifests
- `app/geo/` 50-state boundary check
- `app/services/` source retrieval and caching, the replay engine, report
- `app/api/v2.py` coverage, crops, equations, boundaries, async analysis jobs, results, reports
- `tools/census_states_to_geojson.py` rebuilds `../data/catalogs/us_states_50_cb_2023_20m.geojson`
