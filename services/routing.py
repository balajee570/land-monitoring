"""Driving directions via the public OSRM demo server (free, no key).

We request a full-geometry driving route with turn-by-turn steps. If OSRM is
unreachable we degrade to a geodesic straight line plus a bearing, and we always
provide Google Maps / OpenStreetMap deep links that work on any device without a
key.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

OSRM_BASE = "https://router.project-osrm.org"


@dataclass
class RouteStep:
    instruction: str
    distance_m: float
    name: str = ""


@dataclass
class Route:
    distance_km: float
    duration_min: float
    geometry: List[Tuple[float, float]]  # list of (lat, lon)
    steps: List[RouteStep] = field(default_factory=list)
    straight_line: bool = False


def haversine_km(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    r = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def bearing(a: Tuple[float, float], b: Tuple[float, float]) -> str:
    lat1, lat2 = math.radians(a[0]), math.radians(b[0])
    dlon = math.radians(b[1] - a[1])
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    deg = (math.degrees(math.atan2(x, y)) + 360) % 360
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return dirs[round(deg / 45) % 8]


def get_route(start: Tuple[float, float], end: Tuple[float, float]) -> Route:
    """Return a driving :class:`Route` from start to end (each (lat, lon))."""
    try:
        import requests

        url = (f"{OSRM_BASE}/route/v1/driving/"
               f"{start[1]},{start[0]};{end[1]},{end[0]}"
               "?overview=full&geometries=geojson&steps=true")
        resp = requests.get(url, timeout=15)
        data = resp.json()
        if data.get("code") == "Ok" and data.get("routes"):
            r = data["routes"][0]
            coords = [(c[1], c[0]) for c in r["geometry"]["coordinates"]]
            steps: List[RouteStep] = []
            for leg in r.get("legs", []):
                for st in leg.get("steps", []):
                    man = st.get("maneuver", {})
                    typ = man.get("type", "")
                    mod = man.get("modifier", "")
                    name = st.get("name", "")
                    instr = " ".join(x for x in [typ, mod, ("onto " + name) if name else ""] if x).strip()
                    steps.append(RouteStep(
                        instruction=instr or "continue",
                        distance_m=st.get("distance", 0.0),
                        name=name,
                    ))
            return Route(
                distance_km=round(r["distance"] / 1000.0, 2),
                duration_min=round(r["duration"] / 60.0, 1),
                geometry=coords,
                steps=steps,
            )
    except Exception:
        pass

    # Fallback: straight line
    dist = haversine_km(start, end)
    return Route(
        distance_km=round(dist, 2),
        duration_min=round(dist / 40.0 * 60.0, 1),  # assume ~40 km/h
        geometry=[start, end],
        steps=[RouteStep(
            instruction=f"Head {bearing(start, end)} toward the land (straight-line estimate)",
            distance_m=dist * 1000.0,
        )],
        straight_line=True,
    )


def google_maps_link(start: Tuple[float, float], end: Tuple[float, float]) -> str:
    return (f"https://www.google.com/maps/dir/?api=1&origin={start[0]},{start[1]}"
            f"&destination={end[0]},{end[1]}&travelmode=driving")


def osm_link(start: Tuple[float, float], end: Tuple[float, float]) -> str:
    return (f"https://www.openstreetmap.org/directions?engine=fossgis_osrm_car"
            f"&route={start[0]},{start[1]};{end[0]},{end[1]}")
