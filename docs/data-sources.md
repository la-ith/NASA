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
