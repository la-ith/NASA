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
