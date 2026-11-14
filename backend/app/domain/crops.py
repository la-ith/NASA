"""Crop profiles from the crop table (section 18), and the crop families the rotation rules use."""
import sqlite3
from dataclasses import dataclass

TYPE_LABEL = {
    "cereal": "cereal",
    "grain_legume": "grain legume",
    "forage_legume": "forage legume",
    "fallow": "fallow",
    "unclassified": "unclassified crop",
}


@dataclass(frozen=True)
class CropProfile:
    name: str
    crop_type: str
    season: str | None  # 'winter' for supported candidates; None for history-only choices
    water_need_min_mm: float | None  # None: no confirmed figure
    water_source: str | None


def load_crops(db: sqlite3.Connection) -> dict[str, CropProfile]:
    rows = db.execute(
        "SELECT name, crop_type, season, water_need_min_mm, water_source FROM crop"
        " WHERE review_state != 'retired' ORDER BY crop_id"
    )
    return {row[0]: CropProfile(*row) for row in rows}


def candidates(crops: dict[str, CropProfile]) -> list[str]:
    return [name for name, profile in crops.items() if profile.season == "winter"]


def family(crop: str, crops: dict[str, CropProfile]) -> str:
    """'cereal', 'legume', 'fallow' or 'unknown'. Unknown seasons and unclassified crops are 'unknown'."""
    profile = crops.get(crop)
    if profile is None or profile.crop_type == "unclassified":
        return "unknown"
    if profile.crop_type in ("grain_legume", "forage_legume"):
        return "legume"
    return profile.crop_type
