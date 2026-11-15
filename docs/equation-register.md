# Equation register

The executable source is the authority (spec v4.0, section 21.1). This page lists where each equation lives and
which independent reference case tests it. IDs match `backend/app/science/equations.py`; every analysis result
lists the IDs it used.

| ID | Quantity | Code | Independent test (expected values printed by FAO-56, not produced by this code) |
|---|---|---|---|
| FAO56-Eq7, Eq8 | Atmospheric pressure, psychrometric constant | `science/fao56.py` | FAO-56 Example 2 (z = 1800 m: P = 81.8 kPa, γ = 0.054) |
| FAO56-Eq11, Eq12 | Saturation vapour pressure | `science/fao56.py` | Example 3 (24.5 / 15 °C: es = 2.39 kPa) |
| FAO56-Eq13 | Slope of the vapour pressure curve | `science/fao56.py` | Example 18 (Δ = 0.122) |
| FAO56-Eq14, Eq17, Eq19 | Actual vapour pressure | `science/fao56.py` | Examples 5, 6 and 18 |
| FAO56-Eq21, Eq23–25 | Extraterrestrial radiation | `science/fao56.py` | Example 8 (3 Sept, 20°S: Ra = 32.2), Example 18 (Ra = 41.09) |
| FAO56-Eq34, Eq35 | Daylight hours, Angström radiation | `science/fao56.py` | Examples 10 and 18 |
| FAO56-Eq37–40 | Clear-sky, net shortwave, net longwave, net radiation | `science/fao56.py` | Examples 11, 12 and 18 |
| FAO56-Eq47 | Wind speed at 2 m | `science/fao56.py` | Examples 14 and 18 |
| FAO56-Eq6 (with Eq9, Eq42) | Daily ET0, Penman–Monteith | `science/fao56.py` | Example 18, Uccle 6 July: ET0 = 3.88 ≈ 3.9 mm/day |
| FAO56-Eq58, Eq66 | Crop demand ETc = Kc ET0; stage Kc curve | `science/crop.py` | Shape test (Fig. 25 construction) |
| FAO56-Eq62, Eq63, Eq65 | Kc mid / end climate adjustment; RHmin from dewpoint | `science/crop.py` | Standard climate gives no change; limits test |
| FAO56-Eq82, Eq83 | TAW, RAW (homogeneous and layered) | `science/crop.py` | Example 34 (maize, Zr 1.2 m: TAW 108 / 204 / 144 mm) |
| FAO56-Eq80, Eq84, Eq85, Eq88 | Water stress, daily root-zone balance, drainage | `science/water_balance.py` | Example 35 (10 days, Dr from 55 to 104.5 mm; Ks 1.00 to 0.62) |
| FAO56-T22-p | p adjusted for ETc | `science/crop.py` | Limits test (0.1 ≤ p ≤ 0.8) |
| SCS-CN | Daily runoff, curve number | `science/water_balance.py` | Formula test; CN values confirmed in NRCS NEH 630 Subpart E, Figure 630E-1 |
| BALANCE | Mass conservation of the root zone | `science/water_balance.py` | Closure below 1e-9 mm on mixed wet/dry runs, rain-fed and irrigated; checked in every analysis |

Tolerances in the tests are half a unit of the last digit FAO-56 printed, widened only where FAO carried a
rounded intermediate forward; each case says so in `backend/tests/test_fao56.py` and `test_water_balance.py`.

## Audit corrections and pilot metrics

- Eq. 65 uses late-stage wind/RHmin means; Eq. 62 uses mid-stage means. Shared demand preparation handles soil and climate-only paths with consistent applicability checks.
- SSURGO restrictive layers cap depth; root development was not invented without sourced parameters. Fixed maximum rooting depth remains disclosed.
- CN values are confirmed in NRCS NEH 630 Subpart E (June 2025), Figure 630E-1 page 2; see data-source register. Storm-to-daily application remains an assumption.
- Pilot conversions: W/m² × 0.0864 -> MJ/m²/day; km/day × 1000/86400 -> m/s; RH fraction × 100 -> percent; ft × 0.3048 -> m; wind height normalization uses Eq. 47.
- Bias = mean(model-reference); MAE = mean(abs(model-reference)); RMSE = sqrt(mean((model-reference)^2)), computed on finite pairs, per output with missingness counts. Seasonal paired totals require at least 146 of 153 valid May–September days, without imputation.
- Station-forced FAO versus published ETo is a method consistency cross-check, not independent environmental validation. No universal percentage tolerance or error target is introduced.
- Engine 2.2.0 excludes negative ET0/condensation and zero TAW; all balance forcings must be finite/nonnegative. Storage-limited ETa implies a matching effective Ks and stress-day flag. Standard ETc is a conditional crop simulation.
- Per-season Kc climate QA exposes original and range-limited stage inputs. Kansas following-midnight station stamps are shifted back exactly one day per provider documentation, including the correct terminal download date; this is an evaluation alignment correction, not a fitted bias adjustment.
