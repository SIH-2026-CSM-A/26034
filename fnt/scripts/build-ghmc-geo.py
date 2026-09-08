#!/usr/bin/env python3
"""Regenerate ``src/officer/dashboard/ghmcWards.ts`` from open GHMC boundary data.

A dev-time build tool, not part of the app or its CI. It downloads the DataMeet GHMC
ward and zone GeoJSON (derived from OpenStreetMap admin_level=10 / 9 relations, ODbL),
simplifies each ward with Douglas-Peucker, projects it equirectangularly with a cos(lat)
aspect correction into a shared 0..1000 viewBox, assigns each ward its GHMC zone by
centroid containment, and writes a static TypeScript module. Ward geometry changes rarely
(the corporation last redrew wards in 2016), so this is run by hand when the source moves,
not on every build — which is why the output is committed rather than generated in CI.

    pip install shapely requests   # or: uv run --with shapely,requests python build-ghmc-geo.py
    python build-ghmc-geo.py

Source: https://github.com/datameet/Municipal_Spatial_Data/tree/master/Hyderabad
License: Open Database License (ODbL) — attribute OpenStreetMap contributors.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from urllib.request import urlopen

from shapely.geometry import shape

RAW = "https://raw.githubusercontent.com/datameet/Municipal_Spatial_Data/master/Hyderabad"
OUT = Path(__file__).resolve().parent.parent / "src/officer/dashboard/ghmcWards.ts"
ZONE_ORDER = ["Central", "East", "South", "West", "North"]
SIMPLIFY_TOLERANCE_DEG = 0.0004  # ~45 m at Hyderabad's latitude
VIEWBOX_WIDTH = 1000.0


def _fetch(name: str) -> dict:
    with urlopen(f"{RAW}/{name}") as response:  # noqa: S310 - fixed trusted host
        return json.load(response)


def build() -> None:
    wards = _fetch("ghmc-wards.geojson")["features"]
    zones = _fetch("ghmc-zones.geojson")["features"]
    zone_shapes = [
        (
            zf["properties"]["name"]
            .replace("Greater Hyderabad Municipal Corporation ", "")
            .replace(" Zone", ""),
            shape(zf["geometry"]),
        )
        for zf in zones
    ]

    min_x = min_y = 1e9
    max_x = max_y = -1e9
    for feature in wards:
        a, b, c, d = shape(feature["geometry"]).bounds
        min_x, min_y = min(min_x, a), min(min_y, b)
        max_x, max_y = max(max_x, c), max(max_y, d)
    kx = math.cos(math.radians((min_y + max_y) / 2))
    span_x, span_y = (max_x - min_x) * kx, (max_y - min_y)
    height = round(VIEWBOX_WIDTH * span_y / span_x, 1)

    def project(lon: float, lat: float) -> tuple[float, float]:
        return (
            round((lon - min_x) * kx / span_x * VIEWBOX_WIDTH, 1),
            round((max_y - lat) / span_y * height, 1),
        )

    def ring_d(coords: list) -> str:
        points: list[tuple[float, float]] = []
        last = None
        for lon, lat in coords:
            point = project(lon, lat)
            if point != last:
                points.append(point)
                last = point
        if len(points) < 3:
            return ""
        return "M" + "L".join(f"{x} {y}" for x, y in points) + "Z"

    def geom_d(geom) -> str:
        simplified = geom.simplify(SIMPLIFY_TOLERANCE_DEG, preserve_topology=True)
        if simplified.is_empty:
            simplified = geom.simplify(SIMPLIFY_TOLERANCE_DEG / 4, preserve_topology=True)
        polys = [simplified] if simplified.geom_type == "Polygon" else list(simplified.geoms)
        return "".join(d for p in polys if (d := ring_d(list(p.exterior.coords))))

    records = []
    for feature in wards:
        match = re.match(r"Ward (\d+) (.*)", feature["properties"]["name"])
        if not match:
            continue
        geom = shape(feature["geometry"])
        centroid = geom.representative_point()
        zone = next((zn for zn, zs in zone_shapes if zs.contains(centroid)), "")
        path = geom_d(geom)
        if not path or not zone:
            raise SystemExit(f"ward {match.group(0)} has no path or no zone")
        records.append((int(match.group(1)), match.group(2).strip(), zone, path))
    records.sort(key=lambda r: (ZONE_ORDER.index(r[2]) if r[2] in ZONE_ORDER else 9, r[0]))

    lines = [
        "// AUTO-GENERATED — do not edit by hand. Regenerate with scripts/build-ghmc-geo.py.",
        "//",
        "// Greater Hyderabad Municipal Corporation (GHMC) ward boundaries, 145 of the 150",
        "// wards. Source: DataMeet Municipal_Spatial_Data (github.com/datameet), derived from",
        "// OpenStreetMap admin_level=10 relations, licensed ODbL. Simplified (Douglas-Peucker,",
        "// tolerance ~0.0004 deg / ~45 m) and projected equirectangular with cos(lat) aspect",
        f"// correction into a 0..1000 x 0..{height} viewBox. Zone assigned by ward centroid within",
        "// the GHMC zone polygons from the same source. Boundaries are real geography; this is not",
        "// a survey of enforcement activity. Missing wards (3, 4, 11, 13, 31, 113) are absent from",
        "// the upstream file and simply do not render.",
        "",
        "export interface GhmcWard {",
        "  /** GHMC ward number, 1..150 (the stable id). */",
        "  num: number",
        '  /** Ward locality name, e.g. "Ameerpet". */',
        "  loc: string",
        "  /** GHMC zone: Central | East | South | West | North. */",
        "  zone: string",
        '  /** Canonical ward label as persisted on a scan, e.g. "Ward 98 Ameerpet". */',
        "  name: string",
        "  /** SVG path data in the shared viewBox. */",
        "  d: string",
        "}",
        "",
        f"export const GHMC_VIEWBOX = {{ width: 1000, height: {height} }} as const",
        "",
        "export const GHMC_WARDS: readonly GhmcWard[] = [",
    ]
    for num, loc, zone, path in records:
        safe = loc.replace('"', '\\"')
        lines.append(
            f'  {{ num: {num}, loc: "{safe}", zone: "{zone}", '
            f'name: "Ward {num} {safe}", d: "{path}" }},'
        )
    lines += [
        "]",
        "",
        "/** Zones in map/render order. */",
        "export const GHMC_ZONES = ['Central', 'East', 'South', 'West', 'North'] as const",
        "",
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes, {len(records)} wards)")


if __name__ == "__main__":
    build()
