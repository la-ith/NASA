# Decision log

Implementation decisions taken while building spec v4.0. "Assumed" items are disclosed in every analysis result.

| Date | Decision | Why | Status |
|---|---|---|---|
| 2026-11-14 | Demo sites: Hays, KS (38.85, -99.33) and Ames, IA (42.03, -93.62) | Contrasting semi-arid and humid systems; complete POWER and SSURGO data verified | Decided |
| 2026-11-14 | First crop subset: maize (grain), soybean, sorghum (grain) | Warm-season crops with full FAO-56 parameters; winter wheat left out because its season crosses freezing months the balance does not model | Decided |
| 2026-11-14 | Tmean = (Tmax + Tmin) / 2 (FAO-56 Eq. 9), not POWER T2M | FAO-56 prescribes it for daily ET0; T2M is still used for the frozen-conditions check | Decided |
| 2026-11-14 | ea from dewpoint (Eq. 14) | FAO-56's preferred humidity route; POWER supplies T2MDEW | Decided |
| 2026-11-14 | γ from POWER surface pressure; Rso from POWER cell elevation | Uses the measured/modelled pressure of the same cell rather than Eq. 7 | Decided |
| 2026-11-14 | Soil: NRCS awc_r for TAW; θ(1/3 bar) - θ(15 bar) shown as a sensitivity value | awc_r is NRCS's official available water capacity; the two differ (e.g. 266 vs 182 mm for maize at Hays) | Decided; reviewer to confirm |
| 2026-11-14 | Dominant SSURGO component; dual hydrologic groups use the undrained (second) letter | Disclosed selection; the undrained group is the conservative runoff choice | Decided |
| 2026-11-14 | Root depth: midpoint of the FAO-56 Table 22 range, constant from planting, capped by soil depth | No local root data; FAO-56 notes constant depth overstates early TAW | Assumed |
| 2026-11-14 | Planting dates: maize 05-01, soybean 05-20, sorghum 06-01 | Typical central U.S. timing; to confirm with USDA NASS Usual Planting Dates | Assumed; user can override |
| 2026-11-14 | Starting depletion 0.5 × TAW | No antecedent soil water data | Assumed; user can override |
| 2026-11-14 | Seasons with any day of mean temperature ≤ 0 °C are excluded | The balance does not model snow or frozen soil (spec 5.3) | Decided |
| 2026-11-14 | Irrigation scenario refills to field capacity when RAW is depleted; net only | FAO-56 standard rule; application efficiency not modelled, so gross irrigation is not reported | Decided |
| 2026-11-14 | Basemap: OpenFreeMap Positron; state outlines from our own boundary file | Free, no key, with attribution; the map still works without basemap tiles. Review usage terms before a public deployment | Decided for the demo |
| 2026-11-14 | /api/v2 for the U.S. release; /api/v1 and the Hebron app (/v1/) kept as regression | Spec v4.0 sections 15 and 21.2 | Decided |
| 2026-11-14 | Chatbot not started | Spec Phase 5 comes after the U.S. web flow; no model provider chosen | Planned |

## Review and pilot decisions — 14 November 2026

- Shared `prepare_demand` ensures soil availability does not alter weather-to-ET0/Kc/ETc methods.
- `decision_year` defaults to current year; only its immediately preceding history year supports inference. Duplicates/future history are invalid; gaps remain unknown.
- Planting dates must exist in every replay year. Mixed-year February 29 is rejected before enqueueing.
- Two pure-computation threads and at most 16 admitted jobs keep event-loop requests responsive. All database access stays in orchestration. Interrupted jobs become terminal on shutdown/restart.
- Session-owned private results replace bearer-ID-only access. Legacy rows are preserved, not publicly exposed.
- POWER station responses serialize returned coordinates at exactly three decimals after four-decimal requests. The adapter now checks that exact provider contract rather than a distance tolerance. Requested and returned points are both recorded.
- The pilot is purposive development sampling, not a probability sample. May–September 2020–2022 only; 2023–2025 temporal holdout and spatial holdout stations are reserved and not evaluated.
- CoAgMet RHmin <= 0.01 is excluded from humidity-derived and published-ET comparisons; raw data is retained. 92 development days in 2020 are flagged. Current official station metadata warns of non-reference surroundings; historical site conditions require confirmation.
- No Fresno aridity correction is adopted. Maricopa is an analogue, not California truth. CIMIS access remains blocked.

## Backend 2.2.0 follow-through — 14 November 2026

- User chose OpenAI API. Use server-side Responses API configuration; no key is embedded. Initial assistant
  selects approved evidence IDs; the server renders claims and numbers. Failure falls back explicitly.
- User requested backend/science work while frontend and account databases are reserved for later. Add only
  operational source/conversation/usage storage. Frontend files remain unchanged in this work.
- Supplemental UTC IMERG/SMAP remain context, not mixed into LST balance forcing. SMAP no-data/source mismatch
  is exposed. USDA CDL classification never overwrites farmer-confirmed crop history automatically.
- Prefer working USDA-hosted CroplandCROS REST services over the timing-out legacy GMU service. Lock year/raster
  and verify classification metadata; separate Hawaii availability, reject Alaska.
- Map backend exposes point-supported values. National rasters/tiles require their own gridded pipeline and
  are not fabricated from selected-point results.
- Correct Kansas following-midnight labels from official documentation, not an error-minimizing lag search.
  Preserve previous raw artifacts and obtain correctly bounded development data. Holdouts remain unused.
- Numerical verification is separate from environmental/field accuracy. Fresno and expert agronomic review
  remain open release gates. No correction is fitted to make irrigation totals match published numbers.


## Three-priority delivery — 14 November 2026

- Freeze provisional engineering gates before opening reserved data. Report all failures; do not tune this engine on those outcomes. These groups are now consumed, and no nationwide or field irrigation qualification follows.
- Preserve numerical engine 2.2.0; API expands to 2.3.0. Scientific readiness explicitly reports the failed screening. Expert agronomic review remains separate from the technical source/assumption review.
- User configured OpenAI privately. Model access is verified, but generation is credit-blocked. Use an explicit quota status and evidence fallback, never pretend a live AI answer succeeded. Add curated English/Arabic crop-care evidence without arbitrary generated claims.
- Use actual NASA GIBS raster imagery for national context; respect units, original transparency and date gaps. Do not invert RGB to fabricate quantitative source values.
- Operator-triggered derived-grid builds are resumable and publish immutable COGs. Missing cells stay nodata. Use each cell's source record rather than interpolate a single farm result. The completed live proof is Kansas, not a precomputed national deficit product.
- Prepare current CIMIS header authentication and verify references only when real data can be retrieved. Public Spatial CIMIS file metadata was accessible but point/full download failed; no values from it are used.
