# Field Shift — Code Review Issue Report

Date: 14 November 2026

Scope: U.S. analysis engine, API v2, source adapters and selected frontend integration logic. Baseline commits: `f9e166a` and `37081bb`, plus the working-tree changes present during review. Application files changed concurrently, so this report is a review snapshot, not certification of a frozen revision. No application fixes were made as part of this review.

## Overall assessment

The repository has a useful separation between provider adapters, physical equations, crop models, orchestration, storage and presentation. Published-reference tests, original-source provenance and explicit historical-replay labels are strengths.

The implementation remains a scientific prototype. Confirmed calculation inconsistency, input-validation gaps and API execution/access concerns should be resolved before public use with private farmer records. Independent environmental and agronomic validation remains separate from numerical verification.

## Evidence and limitations

- Ran `python -m pytest -q` from `backend`, using an isolated review virtual environment with the repository's pinned requirements.
- Observed result: **119 passed, 1 failed**, with one dependency deprecation warning.
- Reproduced the soil/no-soil crop-demand mismatch using the saved Hays, Kansas weather record for 2001 and the maize profile.
- Reproduced acceptance of planting date `02-31`, followed by a calendar exception during calculation.
- Inspected job execution, history handling, result retrieval and map-selection code directly.
- Did not visually certify map rendering, conduct a live-provider accuracy study or load-test concurrent users.
- Concurrent edits include scientific calculations and provider code. Re-run the suite on a frozen revision before closing issues or publishing updated numerical results.

## Findings summary

| ID | Priority | Finding | Evidence status |
|---|---|---|---|
| FS-001 | P1 | Standard crop demand changes when soil data is absent | Reproduced numerically; differing paths confirmed in code |
| FS-002 | P1 | CPU-bound simulation runs on the API event loop | Confirmed execution path; contention not load-tested |
| FS-003 | P2 | Impossible planting dates pass request validation | Reproduced |
| FS-004 | P2 | History chronology is not sufficient to establish the previous crop | Confirmed code path; targeted regression test needed |
| FS-005 | P2 | Job/result access relies on bearer IDs rather than session ownership | Confirmed route/schema inspection |
| FS-006 | P2 | Kansas regression expectation differs from current result | Observed test failure; cause not established |
| FS-007 | P2 | Coverage responses can overwrite a newer map selection | Confirmed unguarded asynchronous assignment; browser reproduction needed |

P1: address before relying on the affected calculation or concurrent public analysis service. P2: address before release of the affected workflow; these priorities do not imply independent field validation.

## FS-001 — Crop demand depends on soil availability

Locations: `backend/app/services/analysis_v2.py`, `simulate_season()` and `simulate_climate_only()`.

The soil-enabled path adjusts crop coefficients using seasonal wind and humidity. The climate-only path builds its Kc curve from the unadjusted table coefficients. Removing soil therefore changes standard crop water demand even when weather, crop and planting date are identical.

Observed reproduction:

| Input/output | Soil present | Soil absent |
|---|---:|---:|
| Site | Hays, Kansas | Hays, Kansas |
| Weather season | 2001 | 2001 |
| Crop and planting | Maize, May 1 | Maize, May 1 |
| Standard seasonal ETc | 903.3 mm | 855.2 mm |
| Reported adjusted Kc mid | 1.28 | 1.20 |

Soil availability should determine whether the water balance can run; it should not silently select another weather/crop demand method.

Recommended correction: extract shared weather-to-ET0 and crop-coefficient preparation, including applicability and finite-value checks. Both paths consume identical demand calculations; the soil-enabled path adds water-balance outputs. The climate-only path currently also lacks the soil-enabled path's explicit non-finite ET0 guard, so consolidate that handling rather than maintaining parallel implementations.

Acceptance criteria:

- For identical crop, weather and calendar, ET0 and standard ETc match within the defined numerical tolerance with or without soil.
- Deficit, storage and irrigation outputs remain unavailable when soil is absent.
- Polar-night/non-finite values are reported as unavailable, not serialized as successful scientific results.
- Reference and regression tests verify both paths without loosening tolerances.

## FS-002 — Background jobs block the event loop during simulation

Location: `backend/app/api/v2.py`, `_run_job()`.

The endpoint creates an asyncio task, but the task directly calls synchronous `run_analysis()`. During that call, the server's event loop cannot service other coroutines in the same worker. Creating a task does not move CPU-bound computation to another worker.

Impact: health/coverage calls, polling and other analyses may be delayed during simulation. The job abstraction is asynchronous for network waits, but not for scientific execution. Exact latency impact has not been measured.

Recommended correction: execute pure simulation in a bounded worker executor or durable job worker. Keep database transactions and ownership checks in an appropriate execution context; do not casually share the existing SQLite connection across workers. Bound admission/concurrency and define shutdown/restart behavior for unfinished jobs.

Acceptance criteria:

- While a deliberately slow analysis runs, unrelated API requests and job polling remain responsive within a declared service target.
- Concurrent jobs cannot corrupt or misattribute results.
- Worker errors produce terminal job states; shutdown/restart does not leave jobs permanently running without recovery status.
- Queue size and concurrent work are bounded.

## FS-003 — Invalid planting dates become internal job failures

Location: `backend/app/api/v2.py`, `AnalysisRequestV2.check_period_and_dates()`; downstream `planting_date()` in `analysis_v2.py`.

The regular expression checks the `MM-DD` shape and individual numeric ranges, not whether the date exists. A request with `planting_dates={"maize_grain":"02-31"}` is accepted. The calculation later raises `ValueError: day is out of range for month`.

Impact: user input errors are discovered only after a job is created and may trigger unnecessary source retrieval. February 29 also needs an explicit policy across a multi-year replay.

Recommended correction: validate actual dates before enqueueing. Reject impossible dates with field-specific HTTP 422 errors. Define whether February 29 is rejected for mixed-year replay or handled through a clearly disclosed calendar policy. Reject unknown planting-date crop keys rather than silently accepting ineffective overrides.

Acceptance criteria:

- February 30/31 and April 31 fail before any provider call or job creation.
- Valid month-end dates succeed.
- February 29 has deterministic, tested behavior for leap and non-leap years.
- Errors identify the affected crop/date field.

## FS-004 — Previous-crop inference ignores chronology gaps

Locations: `backend/app/services/run_v2.py`, `run_analysis()`; `backend/app/api/v2.py`, `HistoryItem` and `AnalysisRequestV2`.

The engine sorts submitted history and uses the final entry as the preceding crop. It does not establish that this entry belongs to the season immediately before an explicitly defined decision season. Request validation also permits duplicate history years and future entries up to 2100.

Impact: an old record can be described as the previous season, and a future or conflicting entry can influence current-practice inference and rotation notes. Historical replay years and the user's decision/history period need distinct semantics.

Recommended correction: define an explicit decision/candidate season, validate unique history season identifiers and reject future/inconsistent entries. Infer current practice or a rotation transition only from the immediately preceding known season. Preserve gaps as unknown; allow explicit current-practice selection when inference is unavailable.

Acceptance criteria:

- A gap immediately before the decision season does not inherit an older crop.
- Future and duplicate/conflicting history entries are rejected or explicitly resolved.
- Explicit unknown remains unknown.
- Replay climate years do not accidentally redefine farmer history.

## FS-005 — Missing session ownership on job and result routes

Locations: `backend/app/api/v2.py`, `job()`, `_load()` and report retrieval; `backend/app/db/schema_v2.sql`.

Jobs and analyses are retrieved using their IDs alone. The database describes token possession as demo access control; routes do not check a session owner. IDs are generated with strong random tokens, which reduces guessing, but any leaked/copied token grants access without an ownership check.

Impact: this does not meet v4.0's session-scoped private-field requirement. Result provenance can include precise requested coordinates even when the top-level public location is rounded.

Recommended correction: associate jobs, analyses and reports with a session/access scope and enforce it on all retrievals. Separate explicitly public sample reports from private reports. Generalize sensitive provenance when intentionally sharing public outputs.

Acceptance criteria:

- Session B cannot retrieve session A's jobs, results or reports merely by possessing their IDs.
- Public sample outputs are deliberately marked public and contain no private geometry.
- Precise coordinates in provenance follow the same sharing policy as field geometry.
- Unauthorized requests do not disclose object existence or sensitive errors beyond the chosen access policy.

## FS-006 — Existing regression suite is not fully passing

Location: `backend/tests/test_engine_v2.py`, `test_kansas_regression_medians()`.

Observed failure: expected median sorghum rain-fed deficit `233.3 mm`, received `233.8 mm`, outside the test's `0.05 mm` tolerance. The review occurred during scientific edits, including Kc-stage adjustment changes. The cause has not been conclusively attributed.

Recommended action: freeze the revision, reproduce the failure and explain the changed output through stage/day diagnostics. If it is a scientifically justified correction, update model/version provenance and expected values with evidence. If it is a defect, correct the calculation. Do not widen tolerance or replace expected numbers merely to obtain a green suite.

Acceptance criteria:

- The full pinned-environment suite passes on a recorded revision.
- Any changed expected outputs have a documented method/input explanation.
- Independent reference examples still pass, separately from regression snapshots.

## FS-007 — Coverage selection has a stale-response race

Location: `frontend/app.js`, `setPoint()`.

Each location selection starts a coverage request and assigns its eventual response to the shared `coverage` state. No selection token/abort check guards this assignment. The analysis run has a token, but coverage selection does not.

Trigger: select location A, then B before A's coverage completes; allow B's response to return first and A's last. The displayed coverage/state can then describe A while the saved form and marker describe B.

Recommended correction: use a monotonically increasing selection identifier and discard stale responses, optionally aborting old requests. Bind displayed coverage to the request geometry/mode and invalidate it when those inputs change. This is an integration fix, not a frontend redesign.

Acceptance criteria:

- A delayed old response cannot overwrite coverage for the active selection.
- Loading/error/success states all belong to the same selected location.
- A mocked out-of-order response test covers the scenario.

## Scientific questions requiring investigation, not established defects

1. Fresno's reported high maize irrigation estimate: compare matched ET0 observations and separate weather, Kc, crop calendar, soil and irrigation-policy effects. Do not equate net irrigation with gross applied water or crop ET.
2. Constant maximum rooting depth and assumed initial depletion: quantify sensitivity and disclose applicability; they are documented assumptions, not independently validated defaults nationwide.
3. SSURGO capacity alternatives and component selection: document units, layer integration, gaps/restrictions and selection uncertainty.
4. Curve-number runoff: confirm the original NRCS reference and management assumptions. Water conservation does not validate runoff partitioning.
5. Independent validation: conduct spatially and temporally separated evaluation. Passing FAO examples demonstrates implementation consistency; it does not establish field accuracy.

Concurrent work may address some items; inspect the resulting code and evidence before changing their status to resolved.

## Recommended fix sequence

1. Freeze a review revision and explain the failing regression.
2. Unify demand calculations and applicability handling.
3. Correct calendar/history validation.
4. Isolate computation from the API event loop and add access ownership before private/public deployment.
5. Fix the coverage-selection race without replacing the user's frontend design.
6. Complete the Fresno investigation and start the independent validation study.

Do not expand crop, geographic or AI scope to compensate for unresolved analysis defects. Re-run affected reference, integration and regression tests after each scientific change, then run the full suite before reporting release readiness.

## Follow-up resolution — 14 November 2026

The original report above is preserved as a historical review snapshot. Follow-up code addresses FS-001 through FS-007. FS-006 was explained by the audited late-stage Kc correction; expected regression values were updated with comments, not widened tolerances. New tests exercise demand equality, invalid calendars/history, event-loop responsiveness, cross-session denial, queue admission, restart recovery, and stale frontend responses. Current result: 140 backend tests and one frontend race test passed.

Scientific validation concerns remain open and are tracked in `validation/pilot-validation-report.md`. Pilot results do not certify nationwide accuracy or close Fresno. The map was visually observed, including forced-basemap failure, with evidence in `validation/results/map-fallback.png`. No frontend redesign was performed.
