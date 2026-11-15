# Full application delivery — 14 November 2026

This record supersedes earlier statements that the home page, accounts and national-grid execution were absent. The physical engine remains 2.2.0; no empirical correction was fitted to the evaluated holdouts.

## Application

The root home page introduces the actual product with an original field illustration, real saved Hays 2001–2025 metrics for three crops, US50 geography, source links and explicit research status. Its sample result is generated from the same CLI/engine and source fixtures used by the backend; no invented metrics are used. The workspace supports guest exploration, registration/sign-in, one-time recovery codes, private saved fields, comparisons, seasonal charts, reports, account export/deletion and cited English/Arabic chat. The science page reads equations and validation status from the API.

The field editor renders a MapLibre/OpenFreeMap basemap with Census state outlines, Alaska/Hawaii shortcuts and coordinate entry. The layer selector distinguishes NASA GIBS IMERG rate / SMAP moisture imagery from separately computed crop-season grids. Imagery keeps source dates, gaps, units and legends; numerical point queries are supported only for computed grids. Nearest-neighbor display does not increase native scientific resolution.

Accounts use Argon2id, opaque hashed server-side sessions, HTTP-only SameSite cookies, same-origin writes, bounded hashing and login/recovery throttling. Recovery requires the user's private one-time code; there is no email verification or email recovery service. Passwords and recovery hashes are excluded from exports and validation-error responses. Guest records can be claimed by an account only from the same browser session. Active analyses prevent account deletion until they finish.

Conversations are bounded, private to the same owner and reopen with their saved analysis. The assistant selects server-curated evidence and cannot invent numerical results or mutate fields. API credits were exhausted at the live activation recheck; model access succeeded but response generation did not. Adding usable credits is an external account action. Source-based fallback remains labelled as such.

## National processing

The resumable all-crop operator command targets the full 3,557-point US50 plan for 2020. All crops share validated weather/soil retrieval caches, but each cell's scientific values are computed from its own sources. Per-cell checkpoints, build status, published manifests and per-band valid-cell counts distinguish provider failures, unsupported/frozen cells and missing soil. A complete processing plan is not full agricultural suitability or field accuracy.

See `validation/results/national-grid-delivery.json` for the final artifact IDs, processed/valid counts and checksums. Large COGs, source responses and caches remain in the runtime layer directory and are not committed.

The executed build completed all 3,557 planned locations for each crop (10,671 crop-cell records), with zero provider failures. Valid irrigation/deficit cells are 2,443 for maize, 2,695 for soybean and 2,724 for sorghum. Cold/frozen seasons, negative reference ET0/condensation and zero-water-capacity root zones are excluded; missing mapped soils allow climate-only values but no irrigation value. All 50 states have planned records; this is not a claim that every state has applicable warm-season crop outputs.

Verification checked the three COG byte checksums, canonical publication record hashes, actual per-band valid counts and 9,887 cached canonical source JSON hashes: 3,557 POWER, 3,165 SSURGO and 3,165 restriction responses. These are integrity checks, not accuracy estimates. Run `python tools/verify_national_delivery.py` from `backend/` to reproduce them.

Final automated verification: 193 backend tests and four JavaScript tests pass. Browser checks covered the home page at desktop/mobile widths, sign-in with a disposable local account, private field/history display, a completed saved example, the map and scientific layer controls, and the labelled cited chat fallback. One existing Starlette/AnyIO deprecation warning remains.

## Reproduction and deployment

Use the root README for local setup. `compose.yaml` builds one image serving both frontend and API and persists `/var/lib/field-shift` in the `field-shift-data` volume. Private keys are read server-side from an optional ignored env file and are excluded from the image by `.dockerignore`.

To populate an otherwise empty deployment volume, either run the operator command in the container or transfer the local layer directory (including published COGs/manifests/records) to `/var/lib/field-shift/layers`. For example, with the application running:

```text
docker compose exec app python tools/build_scientific_grid.py --year 2020 --all-crops --concurrency 3
```

Back up the SQLite database with SQLite's online backup API and copy immutable layer artifacts separately. Stop the service for a simple filesystem snapshot of the entire volume; copying a busy SQLite file alone is not a consistent backup. Protect backups because accounts, field locations and chats are private. The volume must be writable by the image's non-root fieldshift user.

Configure an HTTPS reverse proxy to forward the original Host and X-Forwarded-Proto, and allow uvicorn to trust forwarding headers only from the actual proxy. Keep the app's published port on loopback. Cookies become Secure when the application sees HTTPS. Use one worker; in-process background jobs are not a distributed queue. Restarting during a job causes it to be recorded as interrupted rather than falsely complete.

Docker is not installed on this workstation, so image build/runtime execution has not been verified locally. The included CI builds the image after backend/JavaScript tests. No cloud host/domain has been configured and no public deployment is claimed. Sites static/Worker hosting cannot run this Python/GDAL backend without a separately hosted API.

## Scientific limits

FAO example agreement, strict NASA units/date checks and water-balance closure verify calculations. Frozen independent station-season evaluation returned `not_qualified`; observed crop-water/irrigation accuracy and expert review remain pending. The Fresno CIMIS comparison is successful reference-weather validation work but does not establish actual crop irrigation accuracy. Existing evaluated holdouts are consumed and cannot become fresh validation after tuning.

National maps currently publish a single 2020 crop-season scenario, not a 25-year national aggregate. Alaska/Hawaii geometry and source coverage are supported; default warm-season crop calendars are not agronomically confirmed there. Palestine remains outside this US release. Direct numerical Earthdata SMAP L4 ingestion, PRISM, additional crops, field sensors, user email delivery and production distributed infrastructure are separate future work.
