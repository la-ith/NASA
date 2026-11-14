# Pilot validation and review-fix report

Date: 14 November 2026. Engine 2.1.0. Purposive development pilot, not a probability sample.
No nationwide accuracy, crop-yield accuracy or field irrigation accuracy is established.

## Evaluation design

Development: May–September 2020–2022, 153 daily labels per season. Temporal holdout 2023–2025 and spatial holdout stations remain reserved and were not downloaded by this runner. Raw responses are saved with request URLs, retrieval UTC and SHA-256 hashes in data/validation/raw/. Normalized reference values and QA flags are saved in results/normalized_*.json.

Daily labels align by calendar date. POWER uses local solar time; exact station observation-window equivalence has not been verified. Daily differences therefore include possible time-window mismatch.

## Development environmental comparisons

Bias is model minus reference. ET0 units below are mm/day. Comparisons are diagnostic, not a release accuracy certification.

| Station | Year | Paired days | Excluded/missing | Bias | MAE | RMSE |
|---|---:|---:|---:|---:|---:|---:|
| az06 | 2020 | 153 | 0 | 0.316 | 0.744 | 0.915 |
| az06 | 2021 | 153 | 0 | 0.018 | 0.551 | 0.688 |
| az06 | 2022 | 153 | 0 | 0.096 | 0.672 | 0.854 |
| ftc01 | 2020 | 61 | 92 | 1.613 | 1.613 | 1.818 |
| ftc01 | 2021 | 153 | 0 | 1.244 | 1.261 | 1.429 |
| ftc01 | 2022 | 153 | 0 | 1.132 | 1.139 | 1.325 |
| hays | 2020 | 153 | 0 | 0.292 | 1.355 | 1.726 |
| hays | 2021 | 149 | 4 | -0.142 | 1.508 | 1.916 |
| hays | 2022 | 153 | 0 | 0.163 | 1.809 | 2.258 |

Full per-output metrics for Tmax, Tmin, ea, solar radiation, wind, daily ET0 and precipitation are in results/pilot-development.json. Seasonal ET0/rain totals require at least 146/153 paired valid days (95%). Totals sum those paired days without filling gaps. Seasonal metrics report bias/MAE/RMSE over eligible development seasons only; a season with incomplete paired days is not an observed complete total.

## Quality and reference limitations

- AZMET: eto_pen_mon is the published reference; meta_needs_review=1 excludes the day. Wind measured at 3 m is converted using FAO-56 Eq. 47.
- CoAgMet: RH fractions follow the official API documentation despite the CSV units row saying %. RHmin <= 0.01 is retained in raw data but excluded from humidity-derived quantities and published ETo comparison, because that ETo can inherit the suspect humidity. This removes 92 development days in 2020. Solar daily mean W/m² is multiplied by 0.0864; wind km/day is multiplied by 1000/86400. Station elevation is 5120 ft = 1560.576 m. A 6.6-ft wind-height assumption still needs station-era confirmation. Current official station metadata warns that surroundings no longer meet reference conditions; historical site maintenance for the study period needs verification.
- Kansas Hays: no published ETo was used. Reference ET0 is our FAO-56 equation forced by station measurements (ea from RH extremes, measured pressure, SR in MJ/m²/day). It checks input representativeness with the same method, not independent model validation.

## Numerical verification versus environmental validation

FAO worked examples and balance closure verify numerical implementation. Station-forced FAO-56 versus AZMET/CoAgMet published ETo is a method consistency cross-check, not independent environmental validation or exact-equation identity: reference methods, rounding and inputs can differ. Its metrics are reported separately as method_crosscheck. Kansas has no such independent published-ET comparison.

The POWER-versus-station measurements are a limited external development comparison. POWER meteorology uses MERRA-2 reanalysis; its gauge-corrected precipitation may partly depend on overlapping station networks. CERES-based solar radiation and local pyranometers are different observation sources. Ground observations also have uncertainty; turf/irrigated or mixed station surroundings differ from coarse grid averages. No agronomic reviewer has validated crop profiles or irrigation outcomes.

## Fresno status: unresolved

The prior diagnostic reproduced median maize net irrigation 1066.1 mm and ETc 1072.6 mm. Documented sensitivities and daily flux diagnostics are in results/sensitivity_ca_fresno.json and results/diagnostics_ca_fresno_maize.json. No parameters were fitted to published California numbers. CIMIS comparison remains blocked by unavailable registered API access; no CIMIS observations are invented.
Maricopa is an irrigated-desert analogue, not a California validation station. Development daily ET0 bias there is positive but varies strongly by year (see table); it does not establish the cause or magnitude of the Fresno discrepancy. Aridity correction is not adopted.

## Scientific corrections and before/after evidence

Existing audit fixes: Kc end now uses late-stage weather, restrictive layers cap SSURGO root depth, and provider requests use their explicit documented timeouts. Additional review fixes unify demand calculation across soil/no-soil paths and reject non-finite/frozen applicability consistently. API validation, worker isolation, access scope and stale coverage handling are documented in the issue report.

The following table comes from the preserved medians_before_fixes.json and medians_after_fixes.json. Those files capture the earlier scientific audit, not every subsequent review change. They are regression evidence, not measured field improvement.

| Site | Crop | Output (mm) | Before | After | Change |
|---|---|---|---:|---:|---:|
| ks_hays | maize_grain | rainfed_deficit | 371.7 | 371.7 | 0.0 |
| ks_hays | maize_grain | irrigated_net_irrigation | 503.3 | 503.3 | 0.0 |
| ks_hays | soybean | rainfed_deficit | 415.2 | 415.6 | 0.4 |
| ks_hays | soybean | irrigated_net_irrigation | 540.4 | 540.5 | 0.1 |
| ks_hays | sorghum_grain | rainfed_deficit | 233.3 | 233.8 | 0.5 |
| ks_hays | sorghum_grain | irrigated_net_irrigation | 355.6 | 355.6 | 0.0 |
| ia_ames | maize_grain | rainfed_deficit | 59.5 | 59.5 | 0.0 |
| ia_ames | maize_grain | irrigated_net_irrigation | 138.7 | 138.7 | 0.0 |
| ia_ames | soybean | rainfed_deficit | 127.6 | 129.3 | 1.7 |
| ia_ames | soybean | irrigated_net_irrigation | 231.3 | 231.3 | 0.0 |
| ia_ames | sorghum_grain | rainfed_deficit | 27.6 | 27.6 | 0.0 |
| ia_ames | sorghum_grain | irrigated_net_irrigation | 150.3 | 150.3 | 0.0 |
| ca_fresno | maize_grain | rainfed_deficit | 974.7 | 974.7 | 0.0 |
| ca_fresno | maize_grain | irrigated_net_irrigation | 1066.1 | 1066.1 | 0.0 |
| ca_fresno | soybean | rainfed_deficit | 977.5 | 977.3 | -0.2 |
| ca_fresno | soybean | irrigated_net_irrigation | 1058.7 | 1058.5 | -0.2 |
| ca_fresno | sorghum_grain | rainfed_deficit | 712.5 | 712.8 | 0.3 |
| ca_fresno | sorghum_grain | irrigated_net_irrigation | 845.5 | 845.2 | -0.3 |

## Map and engineering verification

Observed in an actual rendering browser: U.S. basemap and state outlines; Alaska and Hawaii shortcuts; outline-only fallback after forcing the style URL to fail in a temporary local harness. Screenshot: results/map-fallback.png. Attu at 52.93 N, 173.2 E was accepted by typed coordinate selection and reported Alaska with source coverage; an exact mouse click on the island is not certified. The frontend design was not redesigned. Backend/JS test results and review issue dispositions are recorded in implementation-status.md and code-review-issues-2026-11-14.md.

## Next milestone and blockers

Resolve station-era metadata and day-window alignment; review crop/soil/management assumptions; obtain a California reference; define output-specific acceptance thresholds before evaluating any holdout. Keep nationwide selection distinct from model applicability. Do not tune on held-out years/stations.

## Primary references

- FAO-56: https://www.fao.org/4/x0490e/x0490e00.htm
- AZMET methods/wind height: https://extension.arizona.edu/sites/extension.arizona.edu/files/pubs/az1324.pdf
- AZMET raw daily endpoint: see the exact URLs in raw download manifests.
- CoAgMet units: https://coagmet.colostate.edu/data/doc.html
- CoAgMet station metadata: https://coagmet.colostate.edu/station_details.php?station=FTC01
- Kansas variables: https://mesonet.k-state.edu/rest/variables/
- Kansas service: https://mesonet.k-state.edu/rest/
- POWER methodology: https://power.larc.nasa.gov/docs/methodology/
