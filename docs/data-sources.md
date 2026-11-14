# Data sources and evidence register

What is integrated, how it was verified, and what is still only planned. Retrieval dates are UTC.

## Integrated

| Source | Use | Access | Verified | Fixtures |
|---|---|---|---|---|
| NASA POWER Daily API v2.10.3, community AG | Daily weather for FAO-56: PRECTOTCORR, T2M, T2M_MAX, T2M_MIN, T2MDEW, RH2M, WS2M, ALLSKY_SFC_SW_DWN, PS | `adapters/power.py`, live or cached 30 days | Units read from a live response on 2026-11-14: mm/day, C, %, m/s, MJ/m^2/day, kPa. Header sources: MERRA2, SYN1DEG, POWER. Fill value -999.0, time standard LST | `data/fixtures/power_ks_hays_2001_2025.json`, `power_ia_ames_2001_2025.json` (9,131 days each, 0 missing) |
| USDA NRCS SSURGO via Soil Data Access | Horizon available water capacity (awc_r), θ at 1/3 and 15 bar, hydrologic soil group | `adapters/ssurgo.py`, live or cached | Live queries on 2026-11-14 at Hays KS (Harney silty clay loam, C), Ames IA (Clarion loam, B), Fresno CA (Hanford sandy loam, A), Palmer AK (Bodenburg silt loam, B), Maui HI (Waiakoa cobbly silty clay loam, C) | `data/fixtures/ssurgo_ks_hays.json`, `ssurgo_ia_ames.json` |
| U.S. Census Bureau cartographic boundary, states, 2023, 1:20M | 50-state scope check and map outlines | `geo/boundaries.py`; built by `tools/census_states_to_geojson.py` | 50 states; Alaska's 47 parts span -179.17° to +179.77° | `data/catalogs/us_states_50_cb_2023_20m.geojson` |
| FAO-56 Tables 11, 12, 22 | Crop stages, Kc, height, rooting depth, p | `data/catalogs/crops_us.json` | Rows read on fao.org on 2026-11-14 (maize grain, soybeans, sorghum grain) | — |
| USDA SCS TR-55 Table 2-2b | Curve numbers 67/78/85/89 for row crops, straight row, good condition | `adapters/ssurgo.py` | Matching values in several secondary reproductions; the scanned original did not extract cleanly. **Verify against the NRCS original.** | — |

## Not integrated yet (shown as "not_integrated" in coverage)

USDA CDL / CroplandCROS (crop history is entered by the user), GPM IMERG, SMAP, PRISM, Landsat/MODIS/Sentinel-2,
ECOSTRESS/OpenET, SRTM, and the other catalog entries in spec v4.0 section 17.

## Required acknowledgements

- "The data was obtained from National Aeronautics and Space Administration (NASA) Langley Research Center's
  Prediction Of Worldwide Energy Resources (POWER) project funded through the NASA Earth Science Division."
- Soil Survey Staff, Natural Resources Conservation Service, United States Department of Agriculture. Soil Survey
  Geographic (SSURGO) Database, via Soil Data Access.
- Basemap: OpenFreeMap (OpenMapTiles, © OpenStreetMap contributors), attribution shown on the map.

## Evaluation-only sources and primary audit references

Exact reference/POWER request URLs, retrieval UTC and SHA-256 are saved in `data/validation/raw/`; station QA and metrics are in `docs/validation/results/`. Reference downloads are limited to development 2020–2022. Applicability-only locations use 2020 POWER and SSURGO coverage checks, not accuracy metrics.

| Source | Units / handling | Official reference |
|---|---|---|
| AZMET az06 | Published eto_pen_mon mm/day; temperature C; ea kPa; solar MJ/m²/day; wind m/s at 3 m normalized by FAO Eq. 47; exclude meta_needs_review=1 | https://extension.arizona.edu/sites/extension.arizona.edu/files/pubs/az1324.pdf ; exact data URLs in raw manifests |
| CoAgMet ftc01 | ASCE short-reference ETo mm/day; RH fractions despite CSV percent header; W/m² times 0.0864; km/day times 1000/86400 | https://coagmet.colostate.edu/data/doc.html |
| CoAgMet site metadata | Elevation 5120 ft = 1560.576 m; 6.6-ft wind height is a network-based working assumption pending station-era confirmation; metadata warns non-reference surroundings | https://coagmet.colostate.edu/station_details.php?station=FTC01 |
| Kansas Mesonet Hays | SR MJ/m²/day; wind 2 m; pressure kPa; ea from RH extremes; reference ET0 uses our FAO calculation, not published ETo | https://mesonet.k-state.edu/rest/ ; https://mesonet.k-state.edu/rest/variables/ |
| NRCS NEH 630 Subpart E, amended June 2025 | Figure 630E-1 page 2 confirms CN 67/78/85/89, row crops / straight row / good condition | https://directives.nrcs.usda.gov/sites/default/files2/1749749646/Subpart%20E%20%E2%80%93%20Runoff%20Curve%20Numbers.pdf |
| SSURGO 2.3.2 metadata | Page 9: awc is a volume fraction including fragments and adjustments; need not equal unadjusted FC-WP attributes | https://www.nrcs.usda.gov/sites/default/files/2022-08/SSURGO-Metadata-Table-Column-Descriptions-Report.pdf |

The earlier request to check CN values against a primary source is resolved by the NRCS reference above. Table confirmation does not validate local runoff or management assumptions. POWER precipitation may share gauge information with reference networks; no blanket independence claim is made. Station-day alignment to POWER LST remains unverified. No CIMIS values are used or invented.
