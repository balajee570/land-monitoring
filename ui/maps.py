"""Folium map builders: satellite view, plot footprints, NASA GIBS time layers,
and route rendering. All tile sources are free and keyless.
"""
from __future__ import annotations

import math
from typing import Optional, Tuple

# Free tile sources -----------------------------------------------------------
ESRI_IMAGERY = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "World_Imagery/MapServer/tile/{z}/{y}/{x}"
)
ESRI_ATTR = "Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community"

ESRI_LABELS = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
)

# NASA GIBS WMTS (EPSG:3857 / GoogleMapsCompatible), {date} = YYYY-MM-DD
GIBS_TRUECOLOR = (
    "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/"
    "MODIS_Terra_CorrectedReflectance_TrueColor/default/{date}/"
    "GoogleMapsCompatible_Level9/{{z}}/{{y}}/{{x}}.jpg"
)
GIBS_NDVI = (
    "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/"
    "MODIS_Terra_NDVI_8Day/default/{date}/"
    "GoogleMapsCompatible_Level6/{{z}}/{{y}}/{{x}}.png"
)
GIBS_ATTR = "Imagery courtesy NASA EOSDIS GIBS"


def _new_map(center: Tuple[float, float], zoom: int = 16):
    import folium

    m = folium.Map(location=list(center), zoom_start=zoom, control_scale=True,
                   tiles=None)
    folium.TileLayer(
        tiles=ESRI_IMAGERY, attr=ESRI_ATTR, name="Satellite (Esri World Imagery)",
        max_zoom=19, overlay=False, control=True,
    ).add_to(m)
    folium.TileLayer("OpenStreetMap", name="Streets (OSM)", control=True,
                     overlay=False).add_to(m)
    folium.TileLayer(
        tiles=ESRI_LABELS, attr=ESRI_ATTR, name="Place labels", overlay=True,
        control=True, show=True,
    ).add_to(m)
    return m


def _radius_from_hectare(hectare: Optional[float]) -> float:
    """Radius (m) of a circle whose area equals the parcel area."""
    if not hectare or hectare <= 0:
        return 25.0
    area_m2 = hectare * 10000.0
    return max(8.0, math.sqrt(area_m2 / math.pi))


def add_gibs_layers(m, date_str: str) -> None:
    """Attach NASA GIBS true-color and NDVI overlays for the given date."""
    import folium

    folium.TileLayer(
        tiles=GIBS_TRUECOLOR.format(date=date_str), attr=GIBS_ATTR,
        name=f"NASA MODIS True Color ({date_str})", overlay=True, control=True,
        show=False, max_zoom=9,
    ).add_to(m)
    folium.TileLayer(
        tiles=GIBS_NDVI.format(date=date_str), attr=GIBS_ATTR,
        name=f"NASA NDVI vegetation ({date_str})", overlay=True, control=True,
        show=False, opacity=0.7, max_zoom=6,
    ).add_to(m)


def build_land_map(center: Tuple[float, float], record=None,
                   gibs_date: Optional[str] = None, zoom: int = 16):
    """Satellite map centred on the land, with parcel markers/footprints."""
    import folium

    m = _new_map(center, zoom=zoom)

    folium.Marker(
        location=list(center),
        tooltip="Land location (approx. village centroid)",
        icon=folium.Icon(color="green", icon="tree-conifer", prefix="glyphicon"),
    ).add_to(m)

    if record is not None and getattr(record, "plots", None):
        # Fan plots slightly around the centroid so overlapping markers are
        # visible; real plot geometry needs the cadastral (Bhu-Naksha) map.
        n = len(record.plots)
        for i, plot in enumerate(record.plots):
            angle = (2 * math.pi * i / max(n, 1))
            dlat = 0.0009 * math.cos(angle) * (1 if n > 1 else 0)
            dlon = 0.0009 * math.sin(angle) * (1 if n > 1 else 0)
            pos = (center[0] + dlat, center[1] + dlon)
            popup = folium.Popup(_plot_popup_html(plot), max_width=280)
            folium.Circle(
                location=list(pos),
                radius=_radius_from_hectare(getattr(plot, "rakba_hectare", None)),
                color="#ffb300", weight=2, fill=True, fill_opacity=0.25,
                popup=popup,
            ).add_to(m)
            folium.map.Marker(
                list(pos),
                icon=folium.DivIcon(html=(
                    f'<div style="font-size:11px;font-weight:700;color:#fff;'
                    f'background:#e65100;border-radius:50%;width:20px;height:20px;'
                    f'line-height:20px;text-align:center;">{i + 1}</div>')),
                tooltip=f"Khesra {getattr(plot, 'khesra_no', '?')}",
            ).add_to(m)

    if gibs_date:
        add_gibs_layers(m, gibs_date)

    folium.LayerControl(collapsed=False).add_to(m)
    return m


def _plot_popup_html(plot) -> str:
    kh = getattr(plot, "khesra_no", "—") or "—"
    rak = getattr(plot, "rakba_text", None) or "—"
    ha = getattr(plot, "rakba_hectare", None)
    owner = getattr(plot, "owner", None) or "—"
    ha_s = f"{ha} ha" if ha else "—"
    return (
        f"<b>Khesra / Plot:</b> {kh}<br>"
        f"<b>Rakba (area):</b> {rak}<br>"
        f"<b>Area (approx):</b> {ha_s}<br>"
        f"<b>Owner:</b> {owner}<br>"
        f"<i>Circle size is an approximate footprint, not the real plot shape.</i>"
    )


def build_route_map(start: Tuple[float, float], end: Tuple[float, float], route):
    """Map showing the route polyline between start and land."""
    import folium

    mid = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
    m = _new_map(mid, zoom=11)

    folium.Marker(list(start), tooltip="Start",
                  icon=folium.Icon(color="blue", icon="home", prefix="glyphicon")).add_to(m)
    folium.Marker(list(end), tooltip="Land",
                  icon=folium.Icon(color="green", icon="flag", prefix="glyphicon")).add_to(m)

    if route and route.geometry:
        color = "#1565c0" if not route.straight_line else "#d32f2f"
        dash = None if not route.straight_line else "8"
        folium.PolyLine(
            [list(p) for p in route.geometry], color=color, weight=5,
            opacity=0.8, dash_array=dash,
        ).add_to(m)
        try:
            m.fit_bounds([list(start), list(end)])
        except Exception:
            pass

    folium.LayerControl(collapsed=True).add_to(m)
    return m
