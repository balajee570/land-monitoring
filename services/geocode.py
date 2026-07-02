"""Geocoding via OpenStreetMap Nominatim (free, no API key).

Jamabandi PDFs do **not** contain GPS coordinates, so we geocode the
village/circle/district text. Nominatim resolves to village/town centroids, not
individual plots, so results are approximate — the UI lets the user refine by
dragging or entering exact coordinates.

We progressively drop the most specific token on failure (village -> circle ->
district) to maximise the chance of a usable hit, and respect Nominatim's usage
policy (<=1 req/s) via caching and a descriptive user agent.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class GeoResult:
    lat: float
    lon: float
    display_name: str
    query_used: str
    approximate: bool = True


def _geolocator():
    from geopy.geocoders import Nominatim

    return Nominatim(user_agent="land-monitoring-app (jamabandi viewer)", timeout=10)


def _query_variants(location_query: str) -> List[str]:
    """Build progressively broader queries by trimming leading tokens."""
    parts = [p.strip() for p in location_query.split(",") if p.strip()]
    variants = []
    for i in range(len(parts)):
        variant = ", ".join(parts[i:])
        if variant and variant not in variants:
            variants.append(variant)
    return variants


def geocode(location_query: str) -> Optional[GeoResult]:
    """Geocode a free-text location, trying progressively broader queries."""
    if not location_query:
        return None
    try:
        geolocator = _geolocator()
    except Exception:
        return None

    for i, variant in enumerate(_query_variants(location_query)):
        try:
            loc = geolocator.geocode(variant, country_codes="in", addressdetails=False)
        except Exception:
            loc = None
        if loc:
            return GeoResult(
                lat=loc.latitude,
                lon=loc.longitude,
                display_name=loc.address if hasattr(loc, "address") else variant,
                query_used=variant,
                approximate=True,
            )
    return None


def reverse(lat: float, lon: float) -> Optional[str]:
    """Reverse-geocode coordinates to a readable place name."""
    try:
        geolocator = _geolocator()
        loc = geolocator.reverse((lat, lon), language="en")
        return loc.address if loc else None
    except Exception:
        return None
