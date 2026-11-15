# Field Shift

Historical US crop-water comparisons using NASA POWER, USDA SSURGO and FAO-56 physical models.

- `/` — responsive public home page with a reproducible Kansas example.
- `/workspace/` — guest exploration, accounts, private fields, historical comparisons, reports and grounded chat.
- `/science/` — equations, data resolution, sources and current validation limitations.
- `/docs` — FastAPI contracts; `/v1/` retains the older Hebron prototype.

## 2026 judging alignment

| Criterion | What to show | Evidence and limits |
|---|---|---|
| Impact | A farmer enters a field, compares three crop options, and gets practical questions to take to local expertise. | Private field notes, a grounded assistant, an in-app agronomist queue, and an exportable report support the next conversation. No yield, income, or guaranteed crop recommendation is claimed. |
| Creativity | The field’s reported context, NASA weather, mapped USDA soil, and a documented water-balance model meet in one comparison. | Each option shows a relative water-gap score and its main modeled factor; the score is not a failure probability. |
| Validity | Open the methods page and follow the inputs through the FAO-56 calculations and source records. | Automated tests and numerical reference checks verify implementation. Independent farm-level accuracy and agronomic review are still outstanding. |
| Relevance | Show NASA POWER weather entering reference evapotranspiration and the crop water balance, with USDA SSURGO soil informing mapped storage assumptions. | NASA data is part of the calculation. Coverage, missing records, spatial resolution, and field-versus-grid limits are identified. |
| Presentation | Use the saved Hays example: open the map, inspect the three crop cards and main factor, then show the next-step guide and report export. | Close with the model limitations and validation status rather than presenting historical replay as a forecast. |

Suggested demo story: **farmer’s question → field and known context → NASA/USDA evidence → three comparable options → what to check with a local expert**. The home page, `/workspace/?demo=ks_hays`, and `/science/` follow this path.

## Start locally

Python 3.12 is required. From the repository root in PowerShell:

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
Set-Location backend
.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open [Field Shift](http://127.0.0.1:8000/). A saved Kansas example works without external weather access. Live analyses retrieve and validate NASA/USDA records. The web client and API share an origin; no frontend build or JavaScript package installation is required.

After setup, launch from the repository root with `./Start-FieldShift.ps1`. The script also recognizes this workstation's existing review environment, so it can be used immediately here. Use `-Port 8010` if port 8000 is already occupied.

Private configuration belongs in ignored `backend/.env`:

```dotenv
OPENAI_API_KEY=your-private-key
OPENAI_MODEL=your-enabled-model
CIMIS_APP_KEY=your-private-key
FIELD_SHIFT_AI_DAILY_CALL_LIMIT=50
```

Never add that file to Git. OpenAI access requires usable API credits. When unavailable, the assistant displays cited source guidance and labels that mode. CIMIS is an operator validation source, not a browser credential.

## National map scenarios

From `backend/`:

```text
python tools/build_scientific_grid.py --year 2020 --all-crops --concurrency 3
```

This builds one historical season for all three crops on a 3,557-point US50 climate-grid plan, including Alaska and Hawaii. It resumes saved per-cell checkpoints and retains original-source hashes. Publication completeness means every planned point was processed; missing soil, unsuitable/frozen seasons and coastal grid-center gaps remain explicitly no-data. It does not assert valid irrigation estimates everywhere. Point analyses separately replay up to 25 seasons.

Generated rasters and source caches live in `outputs/scientific-layers/`, or `FIELD_SHIFT_LAYER_DIR`. They are runtime artifacts, not embedded in the Git repository or container. Back them up and transfer them to the deployment layer volume to display the computed national layers there.

## Verify

```powershell
Set-Location backend
.venv/Scripts/python.exe -m pytest -q
Set-Location ..
node --test frontend/tests/*.test.mjs
```

The tests include FAO worked examples, conservation, corrupted-source rejection, ownership isolation, account recovery, data export and asynchronous UI checks. Passing tests verify implementation; they do not establish farm-level accuracy.

## Deploy

On a host with Docker Compose v2.24 or later:

```text
docker compose up --build -d
docker compose ps
```

The container serves the entire web app and API on `127.0.0.1:8000`, persists SQLite/source caches/layers in a named volume, runs as a non-root user, and has an HTTP health check. Place an HTTPS reverse proxy in front for public access. Use one API process/instance until jobs and SQLite are replaced by an external queue and shared database. See [deployment and delivery notes](docs/full-app-delivery.md) for data transfer, backups and remaining external requirements.

**Scientific status:** research preview. Independent weather screening did not qualify for nationwide field use. Measured crop-irrigation validation, agronomic review and local calendars are still required. No yield, profit, forecast or certified irrigation accuracy is claimed.
