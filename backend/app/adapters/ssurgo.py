"""USDA NRCS SSURGO soil adapter through Soil Data Access (SDA) (spec v4.0, section 4).

One tabular query returns the map unit at the point, its major components and their horizons. The engine uses
the dominant major component (largest comppct_r) and records that choice; a map unit can contain several soils,
so the result is an estimate for the map unit, not a field measurement. Verified by a live query on 14 Nov 2026.
"""
import asyncio
import math
from dataclasses import dataclass, field, replace

import httpx

from app.adapters import NotCovered, ProviderUnavailable, SourceIntegrityError, content_hash
from app.science.crop import Horizon

URL = "https://SDMDataAccess.sc.egov.usda.gov/Tabular/post.rest"
ADAPTER_VERSION = "ssurgo-sda-1.0.0"
ATTEMPT_TIMEOUT_S = 90.0  # Soil Data Access took 2 s to 63 s per query on 2026-11-14; analyses run as background jobs
COLUMNS = ["mukey", "muname", "cokey", "compname", "comppct_r", "majcompflag", "hydgrp", "hzname",
           "hzdept_r", "hzdepb_r", "awc_r", "wthirdbar_r", "wfifteenbar_r", "sandtotal_r", "claytotal_r"]
TABLE_ALIAS = {"mukey": "mu", "muname": "mu", "cokey": "c", "compname": "c", "comppct_r": "c", "majcompflag": "c",
               "hydgrp": "c"}  # every other column comes from the horizon table (h)
# TR-55 Table 2-2b, row crops, straight row, good hydrologic condition (verify against the NRCS original).
CURVE_NUMBERS = {"A": 67, "B": 78, "C": 85, "D": 89}


def describe_product() -> dict:
    return {"provider": "USDA NRCS", "product": "SSURGO via Soil Data Access (tabular)", "support": "soil map unit polygon",
            "variables": {"awc_r": "cm/cm", "wthirdbar_r": "% volume at 1/3 bar", "wfifteenbar_r": "% volume at 15 bar",
                          "hydgrp": "hydrologic soil group"},
            "license": "U.S. public domain", "adapter_version": ADAPTER_VERSION}


def sql(lon: float, lat: float) -> str:
    """Coordinates are formatted numbers, so nothing from the request is pasted into the SQL as text."""
    return (
        "SELECT " + ", ".join(f"{TABLE_ALIAS.get(c, 'h')}.{c}" for c in COLUMNS)
        + f" FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('point({float(lon):.6f} {float(lat):.6f})') AS k"
        " INNER JOIN mapunit mu ON mu.mukey = k.mukey INNER JOIN component c ON c.mukey = mu.mukey"
        " LEFT JOIN chorizon h ON h.cokey = c.cokey WHERE c.majcompflag = 'Yes'"
        " ORDER BY c.comppct_r DESC, c.cokey, h.hzdept_r"
    )


async def fetch(client: httpx.AsyncClient, lon: float, lat: float) -> dict:
    return await _post(client, sql(lon, lat))


async def _post(client: httpx.AsyncClient, query: str) -> dict:
    """One retry on timeout, network error or 5xx. The per-request timeout overrides httpx's 5 s default."""
    body = {"format": "JSON+COLUMNNAME", "query": query}
    for attempt in (1, 2):
        try:
            async with asyncio.timeout(ATTEMPT_TIMEOUT_S):
                response = await client.post(URL, json=body, timeout=ATTEMPT_TIMEOUT_S)
        except (TimeoutError, httpx.TransportError) as exc:
            problem, retryable = f"no response from Soil Data Access ({exc!r})", True
        else:
            if response.status_code == 200:
                return response.json() if response.content.strip() else {}
            problem, retryable = f"Soil Data Access returned HTTP {response.status_code}", response.status_code >= 500
        if attempt == 1 and retryable:
            await asyncio.sleep(2.0)
            continue
        raise ProviderUnavailable(problem)
    raise AssertionError("unreachable")


@dataclass(frozen=True)
class SoilProfile:
    mukey: str
    map_unit: str
    component: str
    component_percent: float
    hydrologic_group: str  # single letter used for runoff
    hydrologic_group_raw: str
    horizons: list[Horizon]  # NRCS available water capacity by horizon
    fc_wp_horizons: list[Horizon]  # θ(1/3 bar) - θ(15 bar) by horizon, for a sensitivity check
    depth_cm: float  # bottom of the deepest horizon with water data, or the restrictive layer if shallower
    manifest: dict = field(compare=False)
    cokey: str = ""
    restriction: dict | None = None  # shallowest restrictive layer of this component: kind and depth [cm]

    @property
    def curve_number(self) -> int:
        return CURVE_NUMBERS[self.hydrologic_group]


RESTRICTION_COLUMNS = ["cokey", "compname", "comppct_r", "reskind", "resdept_r"]


def restriction_sql(lon: float, lat: float) -> str:
    """Restrictive layers ("nearly continuous layer ... that significantly reduce the movement of water and air through
    the soil or that otherwise provides an unfavorable root environment", SSURGO 2.3.2 corestrictions.reskind)."""
    return (
        "SELECT c.cokey, c.compname, c.comppct_r, r.reskind, r.resdept_r"
        f" FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('point({float(lon):.6f} {float(lat):.6f})') AS k"
        " INNER JOIN component c ON c.mukey = k.mukey LEFT JOIN corestrictions r ON r.cokey = c.cokey"
        " WHERE c.majcompflag = 'Yes' ORDER BY c.comppct_r DESC, c.cokey, r.resdept_r"
    )


async def fetch_restrictions(client: httpx.AsyncClient, lon: float, lat: float) -> dict:
    return await _post(client, restriction_sql(lon, lat))


def apply_restrictions(profile: SoilProfile, raw: dict, retrieved_utc: str) -> SoilProfile:
    """Cap the usable soil depth at the shallowest restrictive layer of the selected component."""
    table = raw.get("Table") if isinstance(raw, dict) else None
    if not table or len(table) < 2:
        raise SourceIntegrityError("the restriction query returned no components, but the soil query did")
    if table[0] != RESTRICTION_COLUMNS:
        raise SourceIntegrityError(f"SSURGO restriction columns differ from the query: {table[0]}")
    rows = [dict(zip(RESTRICTION_COLUMNS, r)) for r in table[1:] if r[0] == profile.cokey]
    if not rows:
        raise SourceIntegrityError("the restriction query does not include the selected soil component")
    layers = sorted((d, r["reskind"]) for r in rows if (d := _num(r["resdept_r"])) is not None)
    manifest = {**profile.manifest, "restrictions": {"content_sha256": content_hash(raw), "retrieved_utc": retrieved_utc,
                                                     "layers": [{"kind": k, "top_cm": d} for d, k in layers]}}
    if not layers:
        return replace(profile, manifest=manifest, restriction=None)
    depth, kind = layers[0]
    if depth < 0:
        raise SourceIntegrityError(f"restrictive layer depth {depth} cm is impossible")
    return replace(profile, manifest=manifest, restriction={"kind": kind, "top_cm": depth},
                   depth_cm=min(profile.depth_cm, depth))


def _num(x: object) -> float | None:
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError) as exc:
        raise SourceIntegrityError(f"SSURGO value {x!r} is not a number") from exc
    if not math.isfinite(v):
        raise SourceIntegrityError(f"SSURGO value {x!r} is not finite")
    return v


def validate_and_normalize(raw: dict, lon: float, lat: float, retrieved_utc: str) -> SoilProfile:
    table = raw.get("Table") if isinstance(raw, dict) else None
    if not table or len(table) < 2:
        raise NotCovered("no SSURGO map unit with a major component at this point")
    if table[0] != COLUMNS:
        raise SourceIntegrityError(f"SSURGO columns differ from the query: {table[0]}")
    rows = [dict(zip(COLUMNS, r)) for r in table[1:]]
    dominant = rows[0]["cokey"]
    rows = [r for r in rows if r["cokey"] == dominant]
    first = rows[0]
    group_raw = (first["hydgrp"] or "").strip()
    if not group_raw:
        raise NotCovered("the dominant soil component has no hydrologic soil group")
    group = group_raw.split("/")[-1]  # dual groups such as C/D: the undrained (second) group, which sheds more water
    if group not in CURVE_NUMBERS:
        raise SourceIntegrityError(f"unknown hydrologic soil group {group_raw!r}")
    horizons, fc_wp = [], []
    for r in rows:
        top, bottom, awc = _num(r["hzdept_r"]), _num(r["hzdepb_r"]), _num(r["awc_r"])
        if top is None or bottom is None:
            continue
        if bottom <= top or awc is not None and not 0.0 <= awc <= 0.7:
            raise SourceIntegrityError(f"SSURGO horizon {r['hzname']} is physically impossible")
        if awc is None:
            break  # stop at the first horizon without water data; deeper soil is treated as unavailable
        horizons.append(Horizon(top, bottom, awc))
        fc, wp = _num(r["wthirdbar_r"]), _num(r["wfifteenbar_r"])
        if fc is not None and wp is not None:
            fc_wp.append(Horizon(top, bottom, (fc - wp) / 100.0))
    if not horizons:
        raise NotCovered("the dominant soil component has no available water capacity data")
    manifest = {
        "dataset_id": content_hash(raw)[:24], "provider": "USDA NRCS", "product": "SSURGO (Soil Data Access)",
        "version": "SDA current release at retrieval", "requested_point": {"lat": lat, "lon": lon},
        "returned_support": {"type": "soil map unit", "mukey": first["mukey"]},
        "selection": "dominant major component by comppct_r", "retrieved_utc": retrieved_utc,
        "content_sha256": content_hash(raw), "adapter_version": ADAPTER_VERSION,
        "reference": "Soil Survey Staff, NRCS, USDA. Soil Survey Geographic (SSURGO) Database, via Soil Data Access.",
    }
    return SoilProfile(first["mukey"], first["muname"], first["compname"], float(first["comppct_r"]), group, group_raw,
                       horizons, fc_wp, horizons[-1].bottom_cm, manifest, first["cokey"])
