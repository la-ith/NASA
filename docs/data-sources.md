# Data sources and evidence register

What is integrated, how it was verified, and what is still only planned. Retrieval dates are UTC.

## Integrated

| Source | Use | Access | Verified | Fixtures |
|---|---|---|---|---|
| NASA POWER Daily API v2.10.3, community AG | Daily weather for FAO-56: PRECTOTCORR, T2M, T2M_MAX, T2M_MIN, T2MDEW, RH2M, WS2M, ALLSKY_SFC_SW_DWN, PS | `adapters/power.py`, live or cached 30 days | Units read from a live response on 2026-11-14: mm/day, C, %, m/s, MJ/m^2/day, kPa. Header sources: MERRA2, SYN1DEG, POWER. Fill value -999.0, time standard LST | `data/fixtures/power_ks_hays_2001_2025.json`, `power_ia_ames_2001_2025.json` (9,131 days each, 0 missing) |
| USDA NRCS SSURGO via Soil Data Access | Horizon available water capacity (awc_r), θ at 1/3 and 15 bar, hydrologic soil group | `adapters/ssurgo.py`, live or cached | Live queries on 2026-11-14 at Hays KS (Harney silty clay loam, C), Ames IA (Clarion loam, B), Fresno CA (Hanford sandy loam, A), Palmer AK (Bodenburg silt loam, B), Maui HI (Waiakoa cobbly silty clay loam, C) | `data/fixtures/ssurgo_ks_hays.json`, `ssurgo_ia_ames.json` |
| U.S. Census Bureau cartographic boundary, states, 2023, 1:20M | 50-state scope check and map outlines | `geo/boundaries.py`; built by `tools/census_states_to_geojson.py` | 50 states; Alaska's 47 parts span -179.17° to +179.77° | `data/catalogs/us_states_50_cb_2023_20m.geojson` |
| FAO-56 Tables 11, 12, 22 | Crop stages, Kc, height, rooting depth, p | `data/catalogs/crops_us.json` | Rows read on fao.org on 2026-11-14 (maize grain, soybeans, sorghum grain) | — |
| USDA SCS / NRCS NEH 630 Subpart E (June 2025), Figure 630E-1 page 2 | Curve numbers 67/78/85/89 for row crops, straight row, good condition | `adapters/ssurgo.py` | Confirmed against the NRCS primary table; see reference below | — |

## Supplemental context adapters (separate from production LST water balance)

| Source | Adapter contract | Live development evidence on 2026-11-14 | Limits |
|---|---|---|---|
| USDA CroplandCROS CDL | USDA-hosted ImageServer catalog lookup by Year, lock one raster ID, identify at EPSG:4326 point with rendering None, verify year/returned point/class against attribute table | Hays 2020: class 176 Grassland/Pasture, catalog LowPS 30 m. Raw catalog/identify/classes retained together | Classified pixel is not confirmed farmer history. Alaska unsupported. Separate Hawaii service; no 2020 raster returned. Year-specific resolution can differ (service contains 10-m and 30-m products) |
| GPM IMERG via POWER Daily | IMERG_PRECTOT, AG community, UTC, mm/day; require IMERG source metadata for valid values | 3/3 valid Hays daily values, 2020-05-01–03 | UTC context is not silently mixed with LST daily forcings; source version/run metadata only as supplied by gateway |
| SMAP aliases via POWER Daily | SFMC/RZMC, UTC, m3 m-3; source must confirm SMAP for any valid values; reject silent MERRA-2 replacement | Hays 2020-05-01–03 returned 0/6 valid values, `no_data` | Availability is not established by catalog presence. No direct Earthdata L4 download or model coupling claimed |

Raw payloads and retrieval manifests: `data/validation/raw/backend_*.json`. Summary:
`docs/validation/results/backend-source-checks.json`. `/coverage` returns `unchecked` for unqueried supplemental
products, not guaranteed source coverage. Queries are owner-scoped and retain immutable artifacts.

Primary discovery/contracts:

- USDA developer entry: https://www.nass.usda.gov/developer/index.php
- USDA portal catalog: https://pdi.scinet.usda.gov/portal/sharing/rest/search
- CONUS service: https://pdi.scinet.usda.gov/image/rest/services/CDL_WM/ImageServer
- Hawaii service: https://pdi.scinet.usda.gov/image/rest/services/CDL_WM_Hawaii/ImageServer
- ImageServer identify: https://developers.arcgis.com/rest/services-reference/enterprise/identify-image-service/
- POWER hydrology: https://power.larc.nasa.gov/docs/methodology/data/sources_hydrology/
- POWER daily parameter catalog: https://power.larc.nasa.gov/api/system/manager/parameters?community=ag&temporal=daily

The old CropScape GMU endpoint timed out in a direct live probe; integration uses the working USDA-hosted
CroplandCROS service instead. POWER hydrology documentation and the live manager differ over HY-community
support: the live manager rejected HY. The tested adapter uses AG and checks returned source identity/units.

## Pending sources

PRISM, Landsat/MODIS/Sentinel-2, ECOSTRESS/OpenET, SRTM and other optional catalog entries remain pending.

## Required acknowledgements

- "The data was obtained from National Aeronautics and Space Administration (NASA) Langley Research Center's
  Prediction Of Worldwide Energy Resources (POWER) project funded through the NASA Earth Science Division."
- Soil Survey Staff, Natural Resources Conservation Service, United States Department of Agriculture. Soil Survey
  Geographic (SSURGO) Database, via Soil Data Access.
- Basemap: OpenFreeMap (OpenMapTiles, © OpenStreetMap contributors), attribution shown on the map.

## Evaluation-only sources and primary audit references

Exact reference/POWER request URLs, retrieval UTC and SHA-256 are saved in `data/validation/raw/`; station QA and metrics are in `docs/validation/results/`. The initial development reference downloads use 2020–2022; the separately frozen reserved-group evaluation adds 2023–2025 at development sites and 2020–2022 at reserved sites. Those groups are now consumed evaluation data. Applicability-only locations use 2020 POWER and SSURGO coverage checks, not accuracy metrics.

| Source | Units / handling | Official reference |
|---|---|---|
| AZMET az06 | Published eto_pen_mon mm/day; temperature C; ea kPa; solar MJ/m²/day; wind m/s at 3 m normalized by FAO Eq. 47; exclude meta_needs_review=1 | https://extension.arizona.edu/sites/extension.arizona.edu/files/pubs/az1324.pdf ; exact data URLs in raw manifests |
| CoAgMet ftc01 | ASCE short-reference ETo mm/day; RH fractions despite CSV percent header; W/m² times 0.0864; km/day times 1000/86400 | https://coagmet.colostate.edu/data/doc.html |
| CoAgMet site metadata | Elevation 5120 ft = 1560.576 m; 6.6-ft wind height is a network-based working assumption pending station-era confirmation; metadata warns non-reference surroundings | https://coagmet.colostate.edu/station_details.php?station=FTC01 |
| Kansas Mesonet Hays | SR MJ/m²/day; wind 2 m; pressure kPa; ea from RH extremes; following-midnight stamp shifted to preceding observation day; reference ET0 uses our FAO calculation, not published ETo | https://mesonet.k-state.edu/rest/ ; https://mesonet.k-state.edu/rest/variables/ ; https://mesonet.k-state.edu/rest/url-builder/ |
| NRCS NEH 630 Subpart E, amended June 2025 | Figure 630E-1 page 2 confirms CN 67/78/85/89, row crops / straight row / good condition | https://directives.nrcs.usda.gov/sites/default/files2/1749749646/Subpart%20E%20%E2%80%93%20Runoff%20Curve%20Numbers.pdf |
| SSURGO 2.3.2 metadata | Page 9: awc is a volume fraction including fragments and adjustments; need not equal unadjusted FC-WP attributes | https://www.nrcs.usda.gov/sites/default/files/2022-08/SSURGO-Metadata-Table-Column-Descriptions-Report.pdf |

The earlier request to check CN values against a primary source is resolved by the NRCS reference above. Table confirmation does not validate local runoff or management assumptions. POWER precipitation may share gauge information with reference networks; no blanket independence claim is made. Kansas day labels are corrected; exact civil/standard-time windows versus POWER LST still need review. No CIMIS values are used or invented.


## National imagery, physical grids and California follow-through

- NASA GIBS allowlist: IMERG precipitation rate (mm/hr), SMAP L4 surface/root-zone moisture (m3/m3), source legends, exact date intervals/gaps and capability hash in `data/catalogs/nasa_gibs_layers.json`. Imagery is US50-masked and does not supply quantitative values by RGB inversion. NASA imagery access is separate from the POWER SMAP alias that returned no data.
- Derived COG pipeline: each populated native meteorological-grid cell uses its own POWER record and cell-centre SSURGO scenario. The live Kansas 2020 maize grid has 80/80 cells; national planning covers 3,557 cell centres across 50 states. National deficit values are not all precomputed. See `scientific-delivery.md`.
- Current CIMIS header-authenticated adapter: `adapters/cimis.py`; needs private CIMIS_APP_KEY. New official documentation: https://cimis.water.ca.gov/web-api/rest-api/latest . The deployed production endpoint rejected a no-key probe with HTTP 401, confirming access is gated. No legacy AppKey URL or copied website token is used.
- Public annual Spatial CIMIS 2020 GeoTIFF: metadata/range access succeeded (EPSG:3310, 366 bands); point-read and full-download attempts failed, so no reference values from it are used or invented. Station comparison still awaits the AppKey.
- Crop-care reference paraphrases: FAO growth-stage sensitivity, NC State soybean water management and Oregon State grain sorghum guidance; English/Arabic text remains bounded to sourced evidence. No source is treated as a local field calibration.

Primary new references:

- https://nasa-gibs.github.io/gibs-api-docs/access-basics/
- https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/1.0.0/WMTSCapabilities.xml
- https://www.fao.org/4/t7202e/t7202e05.htm
- https://content.ces.ncsu.edu/north-carolina-soybean-production-guide/10-water-management-in-soybeans
- https://extension.oregonstate.edu/catalog/em-8794-dryland-cropping-systems-grain-sorghum
