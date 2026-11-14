# Field Shift backend

Python 3.12 + FastAPI. Implements the v3.2 spec (`Field Shift Product Spec v3_2.md`): NASA POWER rainfall with
zero-tolerance validation (16.2), indicators (17), the site check (16.1), rules H1-H3 and R1-R6 (18), the
v3.1 SQLite schema (6.4) and the API (10). It also serves the web app in `../frontend`.

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

On startup the app fetches the pilot record from NASA POWER once and caches it for 30 days. Set
`FIELD_SHIFT_WARMUP=0` to skip that, and `FIELD_SHIFT_DB` to choose the database file (default `field_shift.db`).
The tests run offline from `../data/demo`.
