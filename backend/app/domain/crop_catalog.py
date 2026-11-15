"""Versioned U.S. crop catalog (spec v4.0, section 7): FAO-56 parameters with a source for every value."""
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.science.crop import Stages

CATALOG_FILE = Path(__file__).resolve().parents[3] / "data" / "catalogs" / "crops_us.json"


@dataclass(frozen=True)
class CropProfileV2:
    id: str
    name: str
    family: str  # "cereal" or "legume"
    kc_ini: float
    kc_mid: float
    kc_end: float
    height_m: float
    stages: Stages
    root_depth_m: float
    root_depth_range_m: tuple[float, float]
    p: float
    planting_default: str  # "MM-DD"
    sources: dict


@dataclass(frozen=True)
class Catalog:
    version: str
    review_state: str
    scope: str
    crops: dict[str, CropProfileV2]


@lru_cache(maxsize=1)
def load_catalog() -> Catalog:
    raw = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
    crops = {}
    for c in raw["crops"]:
        s = c["stages_days"]
        crops[c["id"]] = CropProfileV2(
            c["id"], c["name"], c["family"], c["kc"]["ini"], c["kc"]["mid"], c["kc"]["end"], c["height_m"],
            Stages(s["initial"], s["development"], s["mid"], s["late"]), c["root_depth_m"]["used"],
            (c["root_depth_m"]["min"], c["root_depth_m"]["max"]), c["depletion_fraction_p"], c["planting_default"],
            c["sources"])
    return Catalog(raw["catalog_version"], raw["review_state"], raw["scope"], crops)
