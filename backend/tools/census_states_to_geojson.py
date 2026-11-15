"""Convert the Census cartographic boundary shapefile of U.S. states to GeoJSON for the 50 states.

Source: U.S. Census Bureau, 2023 Cartographic Boundary File, States, 1:20,000,000
(https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_state_20m.zip). Coordinates are NAD83
longitude/latitude, used here as WGS 84 (the difference is about 1 m, far below the 1:20M generalization).

Usage: python tools/census_states_to_geojson.py <folder with cb_2023_us_state_20m.*> <output.geojson>
The District of Columbia and Puerto Rico are left out: the v4.0 release scope is the 50 states.
Pure standard library: a minimal reader for polygon shapefiles (shape type 5) and dBASE tables.
"""
import json
import struct
import sys
from pathlib import Path

EXCLUDED = {"DC", "PR"}


def read_dbf(path: Path) -> list[dict]:
    data = path.read_bytes()
    n_records, header_len, record_len = struct.unpack("<IHH", data[4:12])
    fields, offset = [], 32
    while data[offset] != 0x0D:
        name = data[offset:offset + 11].split(b"\0")[0].decode("ascii")
        fields.append((name, data[offset + 16]))
        offset += 32
    records = []
    for i in range(n_records):
        start = header_len + i * record_len + 1  # skip the deletion flag
        row, pos = {}, start
        for name, length in fields:
            row[name] = data[pos:pos + length].decode("latin-1").strip()
            pos += length
        records.append(row)
    return records


def read_polygons(path: Path) -> list[list[list[tuple[float, float]]]]:
    data, offset, shapes = path.read_bytes(), 100, []
    while offset < len(data):
        _, content_words = struct.unpack(">ii", data[offset:offset + 8])
        content = data[offset + 8: offset + 8 + content_words * 2]
        shape_type = struct.unpack("<i", content[:4])[0]
        if shape_type != 5:
            raise ValueError(f"expected polygon shapes (type 5), got {shape_type}")
        n_parts, n_points = struct.unpack("<ii", content[36:44])
        parts = list(struct.unpack(f"<{n_parts}i", content[44:44 + 4 * n_parts])) + [n_points]
        base = 44 + 4 * n_parts
        points = [struct.unpack("<2d", content[base + 16 * k: base + 16 * k + 16]) for k in range(n_points)]
        shapes.append([points[parts[k]:parts[k + 1]] for k in range(n_parts)])
        offset += 8 + content_words * 2
    return shapes


def signed_area(ring: list[tuple[float, float]]) -> float:
    """Shoelace formula. Positive for counter-clockwise rings."""
    return 0.5 * sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]))


def inside(point: tuple[float, float], ring: list[tuple[float, float]]) -> bool:
    x, y, hit = point[0], point[1], False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            hit = not hit
    return hit


def to_multipolygon(rings: list[list[tuple[float, float]]]) -> list:
    """Shapefile outer rings are clockwise and holes counter-clockwise; GeoJSON (RFC 7946) wants the reverse."""
    outers = [r for r in rings if signed_area(r) < 0]
    holes = [r for r in rings if signed_area(r) > 0]
    polygons = [[list(reversed(o))] for o in outers]
    for hole in holes:
        owner = next(i for i, o in enumerate(outers) if inside(hole[0], o))
        polygons[owner].append(list(reversed(hole)))
    return [[[list(p) for p in ring] for ring in polygon] for polygon in polygons]


def main(folder: str, output: str) -> None:
    base = Path(folder) / "cb_2023_us_state_20m"
    records, shapes = read_dbf(base.with_suffix(".dbf")), read_polygons(base.with_suffix(".shp"))
    features = [
        {"type": "Feature",
         "properties": {"statefp": r["STATEFP"], "stusps": r["STUSPS"], "name": r["NAME"]},
         "geometry": {"type": "MultiPolygon", "coordinates": to_multipolygon(rings)}}
        for r, rings in sorted(zip(records, shapes), key=lambda pair: pair[0]["NAME"])
        if r["STUSPS"] not in EXCLUDED
    ]
    collection = {
        "type": "FeatureCollection",
        "name": "us_states_50_cb_2023_20m",
        "source": "U.S. Census Bureau, cb_2023_us_state_20m (2023 cartographic boundary, 1:20,000,000)",
        "features": features,
    }
    Path(output).write_text(json.dumps(collection, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {len(features)} states to {output}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
